import './workMarks.css';

export function PriorityMark({priority}: {priority: string}) {
  return <span className="work-priority-mark" data-priority={priority} aria-hidden="true">
    <i/><i/><i/>
  </span>;
}
