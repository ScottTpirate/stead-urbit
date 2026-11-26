// Host navigation and retained-draft regressions; synthetic transport, no native Home.
import test from 'node:test';
import assert from 'node:assert/strict';
import {ProductJourneyDraftStore, productJourneyRoute, productReadNavigationAllowed, type ProductReadNavigationState, type DocProposalDraft} from '../src/productJourneyState';
import {ProductWorkClient} from '../src/productClient';
import {makeProductWorkDraft, reconcileProductWorkDraft, restoreProductWorkDraft} from '../src/productWorkState';
import {makeDocReviewDraft, restoreDocReviewDraft} from '../src/docChangeReviewState';
import {decodeProductRoute, encodeProductRoute, type ProductRoute} from '../src/productRoutes';
import type {ProductWorkDetail} from '../src/productProtocol';
const id=(n:number)=>'019939ba-4000-7000-8000-'+String(n).padStart(12,'0'),project=id(100),resource=id(101),session='confirmed-ui-partition';
const token={},base:ProductReadNavigationState={projectId:project,currentSession:token,partition:token,pending:false,legacyPending:false,dirtyDocument:false,busy:false,formOpen:false,online:true};
const route:ProductRoute={kind:'doc',project,collection:id(200),document:id(201)};
const saved:ProductWorkDetail={kind:'work',project_id:project,resource_id:resource,container_id:'',resource_revision:'1',work_revision:'1',execution_contract_protocol:'stead.work-contract/2',
  execution_contract_revision:'1',execution_contract_digest:'a'.repeat(64),discussion_sequence:'0',title:'Saved',description:'Saved purpose',acceptance_criteria:'Reviewed',
  type:'task',status:'todo',priority:'none',owner_principal_id:'',worker_principal_id:'',owner_display_name:'',worker_display_name:'',blocked_reason:'',required_outcomes:'{}',
  completion_basis:'',completion_principal_id:'',completion_request_id:'',completion_note:'',legacy_assignment_pending:'no',legacy_assignee_principal_id:'',legacy_assignee_display_name:'',legacy_blocked_pending:'no',legacy_blocked_status:'',legacy_prior_status:''};
test('control and history routes retain exact Doc Change pins and admit only current-partition same-project reading',()=>{
  const exact=productJourneyRoute(project,{kind:'doc-change',workId:resource,changeId:id(300),result:{revision:'2',digest:'b'.repeat(64)}});
  for(const target of [route,exact,productJourneyRoute(project,{kind:'work',workId:resource}),productJourneyRoute(project,{kind:'list'})]){
    assert.equal(productReadNavigationAllowed(base,target),true);
    const history=decodeProductRoute(encodeProductRoute(target));assert.deepEqual(history,target);assert.equal(productReadNavigationAllowed(base,history),true);
  }
  for(const target of [null,{...route,project:id(999)},{kind:'workspace',view:'search'},{kind:'project',project,view:'docs'},{kind:'collection',project,collection:id(200)},
    {kind:'run',project,run:id(900)}] as (ProductRoute|null)[])assert.equal(productReadNavigationAllowed(base,target),false);
  assert.equal(productReadNavigationAllowed({...base,currentSession:{}},route),false);
  assert.equal(productReadNavigationAllowed({...base,currentSession:null},route),false);
  assert.equal(productReadNavigationAllowed({...base,partition:null},route),false);
});
test('dirty Doc, pending command, form, action and offline fences apply equally to a related control and Back route',()=>{
  const back=decodeProductRoute(encodeProductRoute(productJourneyRoute(project,{kind:'work',workId:resource})))!;
  for(const key of ['pending','legacyPending','dirtyDocument','busy','formOpen'] as const){
    const state={...base,[key]:true};assert.equal(productReadNavigationAllowed(state,route),false,key);assert.equal(productReadNavigationAllowed(state,back),false,key);
  }
  assert.equal(productReadNavigationAllowed({...base,online:false},route),false);
  assert.equal(productReadNavigationAllowed({...base,projectId:undefined},back),false);
});
test('A-B-A reading and refreshed saved revisions preserve independent title purpose comment review and proposal drafts',()=>{
  const store=new ProductJourneyDraftStore();store.bind(session);const scope={projectId:project,resourceId:resource,authorityEpoch:'1'};
  const draft=makeProductWorkDraft(scope,session,saved);draft.contract={...draft.contract,dirty:true,value:{...draft.contract.value,title:'Local title λ',description:'Local purpose  \n'}};
  draft.discussion={...draft.discussion,dirty:true,value:'Unsent comment  λ'};store.putWork(draft);
  const other=makeProductWorkDraft({...scope,resourceId:id(102)},session,{...saved,resource_id:id(102)});other.discussion={...other.discussion,dirty:true,value:'Other Work comment'};store.putWork(other);
  const review=makeDocReviewDraft({projectId:project,workId:resource,changeId:id(300)},session);review.decisions={'change.approve':{note:'Independent review note λ',conflicted:false,
    base:{authorityEpoch:'1',generation:'c'.repeat(64),headRevision:'1',resultRevision:'1',resultDigest:'b'.repeat(64)}}};store.putReview(review);
  const proposal:DocProposalDraft={scope:{projectId:project,workId:resource,changeId:id(301)},sessionKey:session,base:{authorityEpoch:'1',headRevision:'0',executionContractRevision:'1',executionContractDigest:'a'.repeat(64),
    outcomeId:id(302),target:{kind:'document',project_id:project,collection_id:id(200),document_id:id(201),expected_revision:'1',base_markdown_sha256:'d'.repeat(64)}},markdown:'Exact local proposal λ  \n',summary:'Local summary',dirty:true,conflicted:false};store.putProposal(proposal);
  assert.equal(store.currentPending(project),false);assert.equal(productReadNavigationAllowed({...base,pending:store.currentPending(project)},route),true);
  const refreshed={...saved,title:'New saved title',description:'New saved purpose',work_revision:'2',execution_contract_revision:'2',execution_contract_digest:'e'.repeat(64),discussion_sequence:'1'};
  const returned=reconcileProductWorkDraft(restoreProductWorkDraft(scope,session,refreshed,store.getWork(project,resource)),refreshed,'2');store.putWork(returned);
  assert.equal(returned.contract.value.title,'Local title λ');assert.equal(returned.contract.value.description,'Local purpose  \n');assert.equal(returned.contract.base,'1');assert.equal(returned.contract.authorityEpoch,'1');
  assert.equal(returned.discussion.value,'Unsent comment  λ');assert.equal(returned.discussion.base,'0');assert.equal(store.getWork(project,id(102)),other);
  assert.equal(restoreDocReviewDraft(review.scope,session,store.getReview(review.scope)),review);assert.equal(store.getProposal(proposal.scope),proposal);
  store.bind('replacement-session');assert.equal(store.hasDraft(),false);assert.equal(store.putWork(returned),false);assert.equal(store.putReview(review),false);assert.equal(store.putProposal(proposal),false);
});
test('unresolved exact requests prevent related reading and are never cloned or silently discarded',async()=>{
  const client=new ProductWorkClient({currentSession:()=>token,query:async()=>{throw Error('No reads in host proof');},command:async()=>{throw Error('No effects in host proof');}});
  const prepared=await client.prepareComment({request_id:id(400),project_id:project,resource_id:resource,authority_epoch:'1'},'0','Exact retained bytes λ');
  for(const phase of ['preparing','saving','unknown','accepted'] as const){
    const store=new ProductJourneyDraftStore();store.bind(session);const scope={projectId:project,resourceId:resource,authorityEpoch:'1'},draft=makeProductWorkDraft(scope,session,saved);
    draft.discussion={...draft.discussion,dirty:true,value:'Exact retained bytes λ'};draft.attempt={section:'discussion',phase,prepared,awaitingReadback:phase==='accepted',message:''};store.putWork(draft);
    assert.equal(productReadNavigationAllowed({...base,pending:store.currentPending(project)},route),false,phase);assert.equal(store.discard(project),false);
    const restored=restoreProductWorkDraft(scope,session,saved,store.getWork(project,resource));assert.equal(restored.attempt?.prepared,prepared);assert.equal(restored.attempt?.prepared?.bytes,prepared.bytes);
  }
});
