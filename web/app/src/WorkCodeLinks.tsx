import { useEffect, useState } from 'react';
import { type Fields, type HomeClient } from './api';
import { ReviewTrail } from './CodeRepository';
import { branchLabel } from './externalReview';
import { Button } from './primitives';

type ReviewResult = { client: HomeClient; project: string; work: string; reviews: Fields[] | null };

export function WorkCodeLinks({ client, project, work, onOpenReview }: {
  client: HomeClient; project: string; work: string; onOpenReview: (proposalId: string) => void;
}) {
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    const save = (reviews: Fields[] | null) => {
      if (active) setResult({ client, project, work, reviews });
    };
    void client.externalReviews(project, work).then(save).catch(() => save(null));
    return () => { active = false; };
  }, [client, project, work, retry]);

  const visible = result?.client === client && result.project === project && result.work === work ? result : null;
  return <section className="work-code-links" aria-label="Linked code changes">
    <h3>Code changes</h3>
    {!visible ? <p role="status">Loading linked change reviews…</p> : visible.reviews === null ? <>
      <p role="status">Change reviews are unavailable.</p>
      <Button variant="quiet" onClick={() => { setResult(null); setRetry(value => value + 1); }}>Retry reviews</Button>
    </> : visible.reviews.length === 0 ? <p>No code changes are linked to this work item.</p>
      : <ul className="external-review-list" aria-label="Linked change reviews">
        {visible.reviews.map(review => <li key={review.proposal_id}>
          <Button variant="quiet" onClick={() => onOpenReview(review.proposal_id!)}>
            <strong><bdi>{branchLabel(review.source_ref!)}</bdi></strong>
            <span>{review.merged_revision ? 'Merged' : review.reviewer ? 'Approved revision' : 'Awaiting review'} · Revision {review.revision}</span>
            <ReviewTrail review={review} includeSource={false} />
          </Button>
        </li>)}
      </ul>}
  </section>;
}
