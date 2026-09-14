// Camada de dominio: tipos e regras puras, sem dependencia de framework ou banco.
// Serve de contrato compartilhado entre a UI, a API e o acesso a dados.

export type SourceKey = "facepe" | "cnpq" | "finep" | "capes";

export interface SourceMeta {
  key: SourceKey;
  label: string;
  orgao: string;
  color: string;
}

// Metadados das fontes (apresentacao). O armazenamento e uma unica collection
// Mongo (`editais`); cada documento se identifica pelo campo `fonte`.
export const SOURCES: Record<SourceKey, SourceMeta> = {
  facepe: {
    key: "facepe",
    label: "FACEPE",
    orgao: "Fundação de Amparo à Ciência e Tecnologia de PE",
    color: "#c0392b",
  },
  cnpq: {
    key: "cnpq",
    label: "CNPq",
    orgao: "Conselho Nacional de Desenvolvimento Científico e Tecnológico",
    color: "#1c7a53",
  },
  finep: {
    key: "finep",
    label: "FINEP",
    orgao: "Financiadora de Estudos e Projetos",
    color: "#2a5298",
  },
  capes: {
    key: "capes",
    label: "CAPES",
    orgao: "Coord. de Aperfeiçoamento de Pessoal de Nível Superior",
    color: "#7a5cbf",
  },
};

export function isSourceKey(value: string): value is SourceKey {
  return Object.prototype.hasOwnProperty.call(SOURCES, value);
}

export interface Edital {
  id: string; // identificador estavel derivado da url_pdf (base64url)
  urlPdf: string;
  source: SourceKey;
  sourceLabel: string;
  orgao: string;
  color: string;
  ref: string;
  titulo: string;
  deadline: string | null; // ISO 8601 (data limite de submissao)
  // ISO 8601 (data em que a FONTE publicou o edital, extraida pelo scraper).
  // E o criterio principal de ordenacao da vitrine. `null` quando a fonte nao
  // expoe a data (CNPq) ou o edital foi salvo antes deste campo existir - nesses
  // casos a ordenacao cai para `createdAt`.
  publishedAt: string | null;
  // ISO 8601 (quando a pipeline salvou o edital pela 1a vez). Reserva de
  // ordenacao quando nao ha `publishedAt`.
  createdAt: string | null;
  areas: string[];
  // true se o e-mail atual (identificado no navegador, sem login) esta na lista
  // de interessados deste edital especifico. Nunca inclui a lista de e-mails
  // inteira aqui - so o booleano relativo a quem esta pedindo.
  interested: boolean;
}

// Versao estendida do Edital, usada so na pagina de detalhamento - os campos
// abaixo ja existem no Mongo (mesmo `resultado` que a pipeline usa pra montar
// o email, ver pipeline/emails/saved_record_email_notifier.py), mas nao valia
// a pena carregar em toda consulta da listagem/grid (que ja tem paginacao pra
// evitar payload grande).
export interface EditalDetail extends Edital {
  descricao: string;
  publicoAlvo: string;
  criteriosPublicoAlvo: string[];
  criteriosProponente: string[];
  observacoes: string[];
  cronograma: string[];
  segmentos: string[];
}

// Validacao simples de formato, sem verificar se o endereco existe de fato -
// o cadastro e sem autenticacao, por design (so digitar o e-mail).
export function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

// Remove tambem espacos internos (nao so as bordas), pra ficar consistente
// com sandbox/import_docentes_interesse.py::normalize_email - sem isso um
// e-mail com espaco residual (ex: "luis. barros@upe.br", visto na planilha
// de docentes) normalizaria diferente entre o import Python e o front,
// impedindo o docente de encontrar o proprio registro.
export function normalizeEmail(value: string): string {
  return value.replace(/\s+/g, "").toLowerCase();
}

export type DeadlineUrgency = "urgent" | "soon" | "calm" | "none";

// Dias restantes ate o prazo (0 = hoje, negativo = expirado, null = sem data).
export function daysUntil(deadlineIso: string | null, now: Date = new Date()): number | null {
  if (!deadlineIso) return null;
  const deadline = new Date(deadlineIso);
  if (Number.isNaN(deadline.getTime())) return null;

  const startOfDay = (d: Date) =>
    Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  const diffMs = startOfDay(deadline) - startOfDay(now);
  return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

export function deadlineUrgency(days: number | null): DeadlineUrgency {
  if (days === null) return "none";
  if (days <= 7) return "urgent";
  if (days <= 20) return "soon";
  return "calm";
}

const MESES = [
  "jan", "fev", "mar", "abr", "mai", "jun",
  "jul", "ago", "set", "out", "nov", "dez",
];

export function formatPtBrDate(iso: string | null): string {
  if (!iso) return "Sem prazo definido";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Sem prazo definido";
  const dia = String(d.getUTCDate()).padStart(2, "0");
  return `${dia} ${MESES[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

// Codificacao reversivel da url_pdf para uso como id em rotas de API.
export function encodeId(urlPdf: string): string {
  return Buffer.from(urlPdf, "utf-8").toString("base64url");
}

export function decodeId(id: string): string {
  return Buffer.from(id, "base64url").toString("utf-8");
}

export interface EditaisPage {
  items: Edital[];
  nextCursor: string | null;
  hasMore: boolean;
}

// Paginacao por cursor sobre uma lista ja ordenada (por data de publicacao,
// ver listEditais em editais-repository.ts). O cursor e o `id` do ultimo
// edital recebido na pagina anterior; a proxima pagina comeca logo depois
// dele na MESMA ordenacao - por isso a lista passada aqui precisa ja estar
// ordenada do jeito que a UI espera ver (publicacao mais recente primeiro,
// com o id como desempate estavel entre datas iguais).
// Cursor desconhecido (item removido entre uma pagina e outra) equivale a
// "fim da lista", em vez de reiniciar do zero - evita duplicar itens.
export function paginateEditais(
  sorted: Edital[],
  cursor: string | null,
  limit: number,
): EditaisPage {
  let start = 0;
  if (cursor) {
    const idx = sorted.findIndex((e) => e.id === cursor);
    start = idx === -1 ? sorted.length : idx + 1;
  }
  const items = sorted.slice(start, start + limit);
  const hasMore = start + items.length < sorted.length;
  return {
    items,
    nextCursor: hasMore ? items[items.length - 1].id : null,
    hasMore,
  };
}
