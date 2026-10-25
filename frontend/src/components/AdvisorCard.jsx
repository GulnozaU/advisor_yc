import { useState } from "react";
import { motion } from "framer-motion";
import { Check, ChevronDown, ExternalLink, Mail, CalendarDays, TrendingDown, BookOpen, X } from "lucide-react";
import { countdown } from "@/lib/format";

const ICON = { thread: Mail, calendar: CalendarDays, market: TrendingDown, playbook: BookOpen };
const PARTS = { S: "Stakes", L: "Loop", U: "Urgency", E: "Effort", impact: "Impact", mult: "Soft-source multiplier", override: "Your override", priority: "Score" };

export const AdvisorCard = ({ it, index, compact, onSend, onDone, onDismiss }) => {
  const [open, setOpen] = useState(false);
  const Icon = ICON[it.source] || Mail;
  const due = countdown(it.deadline);
  const canDraft = it.source === "thread" || it.source === "calendar";
  return (
    <motion.div layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: 48 }}
      transition={{ type: "spring", stiffness: 380, damping: 34 }} className="pcard" data-testid={`advisor-card-${it.id}`}>
      <span className="pnum">{index + 1}</span>
      <div className="pbody">
        <div className="pmeta">
          <span className={`ptype type-${it.kind}`}><Icon size={11} style={{ display: "inline", marginRight: 4 }} />{it.kind}</span>
          <span className={`due due-${due.tone}`} data-testid={`advisor-due-${it.id}`}>{due.text}</span>
        </div>
        <p className="paction" data-testid={`advisor-action-${it.id}`}>{it.action}</p>
        {!compact && it.evidence && <p className="evidence" title="From the source">“{it.evidence.slice(0, 110)}”</p>}
        {!compact && (
          <button className="why-toggle" onClick={() => setOpen(!open)} data-testid={`advisor-why-${it.id}`}>
            Why #{index + 1} <ChevronDown size={14} style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform .2s" }} />
          </button>
        )}
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} className="why-box" data-testid={`advisor-why-box-${it.id}`}>
            <p>{it.why}</p>
            <div className="score-parts">
              {Object.entries(it.score_parts).map(([k, v]) => <span key={k}>{PARTS[k] || k}: <b>{typeof v === "number" ? Math.round(v * 100) / 100 : v}</b></span>)}
            </div>
          </motion.div>
        )}
      </div>
      {!compact && (
        <div className="pactions">
          {canDraft && <button className="btn-soft sm" onClick={() => onSend(it)} data-testid={`advisor-send-${it.id}`}>Send</button>}
          {it.link && <a className="icon-btn" href={it.link} target="_blank" rel="noreferrer" aria-label="Open source" data-testid={`advisor-open-${it.id}`}><ExternalLink size={15} /></a>}
          <button className="icon-btn" aria-label="Done" onClick={() => onDone(it)} data-testid={`advisor-done-${it.id}`}><Check size={16} /></button>
          <button className="icon-btn" aria-label="Dismiss" onClick={() => onDismiss(it)} data-testid={`advisor-dismiss-${it.id}`}><X size={16} /></button>
        </div>
      )}
    </motion.div>
  );
};
