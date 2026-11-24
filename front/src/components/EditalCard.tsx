"use client";

import Link from "next/link";

import {
  Edital,
  daysUntil,
  deadlineUrgency,
  formatPtBrDate,
} from "@/domain/edital";
import { BellIcon, ClockIcon, OutlineStarIcon, StarIcon } from "@/components/icons";

interface EditalCardProps {
  edital: Edital;
  onToggle: (edital: Edital) => void;
}

// Cartao de edital: apresenta os dados e delega a marcacao de interesse (por
// e-mail, sem autenticacao) ao container. O card inteiro leva a pagina de
// detalhamento (/editais/[id]) por um <Link> de verdade no titulo, esticado por
// CSS (`.card-main-link::after`) para cobrir o card todo. Assim o navegador o
// trata como link: botao direito > "abrir em nova guia", Ctrl/Cmd+clique etc.
// A estrela e o link "Acessar Edital" ficam acima dessa camada (z-index).
export default function EditalCard({ edital, onToggle }: EditalCardProps) {
  const days = daysUntil(edital.deadline);
  const urgency = deadlineUrgency(days);
  const daysLabel = days === null ? "-" : `${days}d`;

  return (
    <article className="card" data-interest={edital.interested}>
      <div className="card-head">
        <div>
          <span className="src-chip">
            <span className="src-dot" style={{ background: edital.color }} />
            {edital.sourceLabel}
          </span>
          <div className="ref">Ref: {edital.ref}</div>
        </div>
        <button
          className="star"
          type="button"
          aria-pressed={edital.interested}
          aria-label={edital.interested ? "Remover dos interesses" : "Marcar como interesse"}
          onClick={(e) => {
            const btn = e.currentTarget;
            btn.classList.remove("pop");
            void btn.offsetWidth;
            btn.classList.add("pop");
            onToggle(edital);
          }}
        >
          <StarIcon />
        </button>
      </div>

      <h3 className="title">
        <Link href={`/editais/${edital.id}`} className="card-main-link">
          {edital.titulo}
        </Link>
      </h3>
      <p className="org">{edital.orgao}</p>

      <div className="meta-row">
        <span className={`deadline ${urgency}`}>
          <ClockIcon />
          {formatPtBrDate(edital.deadline)}
          {days !== null && (
            <>
              {" · "}
              <span className="days">{daysLabel}</span>
            </>
          )}
        </span>
        {edital.areas.map((area) => (
          <span className="area-tag" key={area}>
            {area}
          </span>
        ))}
      </div>

      <a
        className="card-link"
        href={edital.urlPdf}
        target="_blank"
        rel="noopener noreferrer"
      >
        Acessar Edital
      </a>

      <div className="status-line">
        {edital.interested ? (
          <>
            <BellIcon /> Você recebe os lembretes deste edital
          </>
        ) : (
          <>
            <OutlineStarIcon /> Marque para receber lembretes de prazo
          </>
        )}
      </div>
    </article>
  );
}
