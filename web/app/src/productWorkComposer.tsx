import {useRef} from 'react';
import {Button, Dialog, OutcomeState} from './primitives';
import {newId} from './protocol';
import type {ProductProperties} from './productProtocol';
import {ProductWorkAttemptState, ProductWorkContractFields, ProductWorkDetails, ProductWorkProperties} from './productWorkFields';
import {adoptProductWorkCreateAuthority, productWorkHasDraft, useProductWorkDraft, type ProductWorkDraft, type ProductWorkEnvironment} from './productWorkState';
import './productWork.css';

export type ProductWorkComposerProps = ProductWorkEnvironment & {open: boolean; onClose: (draft?: ProductWorkDraft) => void};
export function ProductWorkComposer(props: ProductWorkComposerProps) {
  if (!props.supported || props.access !== 'writable') return <Dialog open={props.open} title="Create work item" onClose={() => props.onClose()}>
    <OutcomeState state={!props.supported ? 'unsupported_operation' : props.access === 'revoked' ? 'permission_revoked' : 'read_only'}/>
  </Dialog>;
  return <ActiveComposer {...props}/>;
}
function ActiveComposer(props: ProductWorkComposerProps) {
  const state = useProductWorkDraft(props), {draft, change, locked, pending} = state;
  const title = useRef<HTMLInputElement>(null);
  function submit() {
    if (draft.properties.value.status === 'legacy-blocked') return;
    void state.send('create', () => props.client.prepareCreate({request_id: newId(), project_id: props.scope.projectId,
      resource_id: props.scope.resourceId, authority_epoch: props.scope.authorityEpoch}, draft.properties.value as ProductProperties, draft.contract.value));
  }
  return <Dialog open={props.open} title="Create work item" initialFocus={title} onClose={() => props.onClose(draft)}
    footer={<><Button disabled={pending} onClick={() => props.onClose(draft)}>Cancel</Button>
      <Button variant="primary" disabled={locked || !draft.contract.value.title || draft.attempt?.phase === 'accepted' || draft.conflicts.create || draft.authorityEpoch !== props.scope.authorityEpoch} pending={draft.attempt?.phase === 'saving'} onClick={submit}>Create work item</Button></>}>
    <div className="product-work-composer">
      <ProductWorkContractFields environment={props} value={draft.contract.value} titleRef={title} disabled={locked}
        onChange={value => change(current => ({...current, contract: {...current.contract, value, dirty: true}}))}/>
      <ProductWorkProperties environment={props} value={draft.properties.value} disabled={locked} creating
        onChange={value => change(current => ({...current, properties: {...current.properties, value, dirty: true}}))}/>
      {productWorkHasDraft(draft) && !draft.attempt && <p className="product-work-local">Local draft · not saved</p>}
      {(draft.conflicts.create || draft.authorityEpoch !== props.scope.authorityEpoch) && <p>Your draft is kept. Refresh current access before continuing.
        <Button disabled={locked || draft.authorityEpoch === props.scope.authorityEpoch} onClick={() => change(current => adoptProductWorkCreateAuthority(current, props.scope))}>Keep draft using current access</Button></p>}
      <ProductWorkAttemptState environment={props} draft={draft} retry={state.retry}/><ProductWorkDetails draft={draft}/>
    </div>
  </Dialog>;
}
