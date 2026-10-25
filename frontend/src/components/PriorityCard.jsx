import { Check, GripVertical, Pencil, RotateCcw, Trash2, X } from "lucide-react";
import { countdown } from "@/lib/format";

const IconBtn = ({ label, onClick, children, testId }) => (
  <button type="button" className="icon-btn" aria-label={label} title={label} onClick={onClick} data-testid={testId}>{children}</button>
);

export const PriorityCard = ({ p, index, compact, onEdit, onDone, onDismiss, onReopen, onDelete, dragControls }) => {
  const due = countdown(p.deadline);
  const closed = p.status !== "open";
  return (
    <div className={`pcard ${closed ? "closed" : ""}`} data-testid={`priority-card-${p.id}`}>
      {dragControls && (
        <button type="button" className="grip" aria-label="Drag to reorder" onPointerDown={(e) => dragControls.start(e)} data-testid={`priority-drag-${p.id}`}>
          <GripVertical size={16} />
        </button>
      )}
      {index !== undefined && <span className="pnum">{index + 1}</span>}
      <div className="pbody">
        <div className="pmeta">
          <span className={`ptype type-${p.type}`}>{p.type}</span>
          {p.sample && <span className="psample" data-testid={`priority-sample-${p.id}`}>{p.origin === "research" ? "Researched" : "Sample"}</span>}
          {!closed && <span className={`due due-${due.tone}`} data-testid={`priority-due-${p.id}`}>{due.text}</span>}
          {closed && <span className="psample">{p.status === "done" ? "Done" : "Dismissed"}</span>}
        </div>
        <p className="paction" data-testid={`priority-action-${p.id}`}>{p.action}</p>
        {!compact && (p.who || p.reason) && (
          <p className="preason">{p.who && <b>{p.who}. </b>}{p.reason}</p>
        )}
      </div>
      {!compact && (
        <div className="pactions">
          {closed ? (
            <>
              <IconBtn label="Move back to the list" onClick={onReopen} testId={`priority-reopen-${p.id}`}><RotateCcw size={16} /></IconBtn>
              <IconBtn label="Delete" onClick={onDelete} testId={`priority-delete-${p.id}`}><Trash2 size={16} /></IconBtn>
            </>
          ) : (
            <>
              <IconBtn label="Mark done" onClick={onDone} testId={`priority-done-${p.id}`}><Check size={16} /></IconBtn>
              <IconBtn label="Edit" onClick={onEdit} testId={`priority-edit-${p.id}`}><Pencil size={15} /></IconBtn>
              <IconBtn label="Dismiss" onClick={onDismiss} testId={`priority-dismiss-${p.id}`}><X size={16} /></IconBtn>
              <IconBtn label="Delete" onClick={onDelete} testId={`priority-delete-${p.id}`}><Trash2 size={15} /></IconBtn>
            </>
          )}
        </div>
      )}
    </div>
  );
};
