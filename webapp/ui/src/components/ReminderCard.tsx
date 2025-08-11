import React from "react";

export function ReminderCard(props: {
  icon: React.ReactNode;
  title: string;
  time: string;
  meta?: string;
  onBell?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}) {
  return (
    <div className="reminder-card">
      <div className="icon">{props.icon}</div>
      <div>
        <div className="title" title={props.title}>{props.title}</div>
        <div className="meta">{props.meta ?? ""} {props.time}</div>
      </div>
      <div className="actions">
        {props.onBell &&   <button className="btn" onClick={props.onBell}>🔔</button>}
        {props.onEdit &&   <button className="btn" onClick={props.onEdit}>✏️</button>}
        {props.onDelete && <button className="btn" onClick={props.onDelete}>🗑️</button>}
      </div>
    </div>
  );
}
