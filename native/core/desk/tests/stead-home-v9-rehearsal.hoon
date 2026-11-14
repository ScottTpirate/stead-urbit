::  Synthetic saved-state fixtures through the real Gall load/save arms.
::  These structural proofs do not assert stock-Git or live identity custody.
/+  *test, stead-team, stead-team-config, stead-team-codec, stead-team-owner, stead-code-home, stead-home-handoff, stead-project-retirement, stead-projection, stead-codec, stead-code-pack-anchor, stead-code-pack-push, stead-code-pack-ledger, stead-code-pack-review-board, stead-code-pack-promotion, stead-code-pack-review, stead-code-receive, stead-session, stead-code-git-graph, stead-git
/=  home-agent  /app/stead-home
/=  review-fixture  /tests/stead-code-pack-review-board
=,  stead-code-pack-ledger
=/  promotion=record:stead-code-pack-promotion  saved-record:review-fixture
=/  reviewed=proposal:stead-code-pack-review  reviewed.review.candidate.promotion
=/  current=manifest  base.promotion
=/  destination=scope  destination.current
=/  project=@t  project.destination
=/  bootstrap=@t  '019939ba-4000-7000-8000-000000000006'
=/  main=@t  target.location.item.reviewed
=/  source=@t  source.reviewed
=/  source-key=@t  (bytes-hex:stead-codec source)
=/  digest=@t  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
=/  who=actor
  [~bus '019939ba-4000-7000-8000-000000000002' '019939ba-4000-7000-8000-000000000003' 1 & 2.000.000]
=/  anchor=entry:stead-code-pack-anchor
  [%accepted [current ~zod 1 900.001] [bootstrap who 2]]
=/  anchors=state:stead-code-pack-anchor  (malt ~[[project anchor]])
=/  accepted  (promote (need (open anchor)) promotion accepted-at.promotion)
?>  ?=(%& -.accepted)
=/  external=external-writes:stead-team-owner  (malt ~[[project p.accepted]])
=/  board=state:stead-code-pack-review-board  saved-board:review-fixture
=/  boards=pack-boards:stead-team-owner  (malt ~[[project board]])
=/  pending-board=state:stead-code-pack-review-board  approved-state:review-fixture
=/  pending-boards=pack-boards:stead-team-owner  (malt ~[[project pending-board]])
=/  company-init  (configure:stead-team empty:stead-team '{"protocol":"stead.team-config/1","expected_revision":"0","home":"~zod","origin":"https://home.test","organization_id":"019939ba-4000-7000-8000-000000000005","team_id":"019939ba-4000-7000-8000-000000000006","custody":"local-disposable","runtime":"isolated-fake","bindings":{"~bus":{"principal_id":"019939ba-4000-7000-8000-000000000002","binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"1","active":"yes","expires_at_ms":"2000000","display_name":"Synthetic member"}},"project_creators":{"019939ba-4000-7000-8000-000000000002":"yes"}}' ~zod 1)
=/  member  (need (native-context:stead-team company-init ~bus 1))
?>  =(identity.member who)
=/  create  (decode:stead-team-codec '{"protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000007","project_id":"019939ba-4000-7000-8000-000000000001","resource_id":"019939ba-4000-7000-8000-000000000001","expected_revision":"0","authority_epoch":"1","operation":"project.create","payload":{"organization_id":"019939ba-4000-7000-8000-000000000005","owning_team_id":"019939ba-4000-7000-8000-000000000006","title":"Synthetic review reload","project_key":"REVIEW","preset":"general"}}')
=/  created  (apply-command:stead-team company-init member create 1)
?>  =(1 (lent journal.data.next.created))
=/  company  next.created
=/  team=saved:stead-team-owner  [company *state:stead-projection]
=/  code=persisted:stead-code-home  *persisted:stead-code-home
=/  context=bowl:gall  *bowl:gall
=.  context  context(our ~zod, src ~zod, now (add ~1970.1.1 (mul 2 ~s1)), eny `@uvJ`17, act 5)
=/  initial=agent:gall  ~(. home-agent context)
=/  v9=vase  !>([%stead-home %9 team code [%open 1 ~] ~ anchors external boards])
|%
+$  envelope
  $:  %stead-home  %9  team=saved:stead-team-owner
      code=persisted:stead-code-home  mode=phase:stead-home-handoff
      retired=ledger:stead-project-retirement  packs=state:stead-code-pack-anchor
      external=external-writes:stead-team-owner  reviews=pack-boards:stead-team-owner
  ==
++  reload
  |=  source=vase
  ^-  [cards=(list card:agent:gall) saved=vase row=envelope]
  =/  [cards=(list card:agent:gall) loaded=agent:gall]  (on-load:initial source)
  =/  saved=vase  on-save:loaded
  [cards saved !<(envelope saved)]
++  seal
  |=  input=manifest
  ^-  manifest
  =/  raw  (snapshot-bytes:stead-code-pack-anchor input)
  =/  size  (met 3 raw)
  input(snapshot (hex:stead-codec 64 (sha-256l:sha [size (rev 3 size raw)])))
++  raw-advance
  |=  [db=ledger request=@t attempt=@ud prior=@ux target=@ux pack=manifest now=@ud]
  ^-  ledger
  =/  checked=checked
    :*  destination  snapshot.current.db  generation.db  digest  request
        ~[[source prior target]]  pack
        (malt ~[[target %commit]])  (silt ~[[prior target]])
    ==
  =/  claim=intent
    [destination snapshot.current.db generation.db digest request attempt digest changes.checked]
  =/  allow-all=allow  |=([action:stead-code-receive update] &)
  =/  protected=(set @t)  (silt ~[main])
  =/  staged  (admit db claim who now digest allow-all protected)
  ?>  ?=(%applied -.staged)
  =/  verified  (verify next.staged claim checked who +(now) digest allow-all protected)
  ?>  ?=(%applied -.verified)
  =/  accepted  (commit next.verified claim checked who (add now 2) digest allow-all protected)
  ?>  ?=(%applied -.accepted)
  next.accepted
++  test-home-v9-board-only-load-save-retains-proposal-and-approval
  =/  source=vase
    !>([%stead-home %9 team code [%open 1 ~] ~ anchors *external-writes:stead-team-owner pending-boards])
  =/  restored  (reload source)
  =/  again  (reload saved.restored)
  =/  ok=?
    ?&  ?=(^ cards.restored)
        =(company db.team.row.restored)
        =(code code.row.restored)
        =(anchors packs.row.restored)
        =(pending-boards reviews.row.restored)
        =(~ external.row.restored)
        =([%open 1 ~] mode.row.restored)
        =(~ retired.row.restored)
        =(q.saved.restored q.saved.again)
    ==
  (expect !>(ok))
++  test-home-v9-load-save-retains-exact-promotion-and-history
  =/  restored  (reload v9)
  =/  again  (reload saved.restored)
  =/  db  (~(got by external.row.restored) project)
  =/  review  (~(got by reviews.row.restored) project)
  =/  ok=?
    ?&  ?=(^ cards.restored)
        =(external external.row.restored)
        =(boards reviews.row.restored)
        =(1 generation.db)
        =(pack.decision.candidate.promotion current.db)
        =(~[request.promotion] journal.db)
        =(promotions.db promotions.review)
        =(promotion (~(got by promotions.db) request.promotion))
        =(~ receipts.db)
        ?=(~ pending.db)
        (valid db anchor)
        (valid:stead-code-pack-review-board review)
        =(q.saved.restored q.saved.again)
    ==
  (expect !>(ok))
++  test-home-v9-rejects-missing-mismatched-and-empty-review-history
  =/  later=record:stead-code-pack-promotion  promotion(accepted-at 101)
  =/  altered  board(last 101, promotions (~(put by promotions.board) request.promotion later))
  ?>  (valid:stead-code-pack-review-board altered)
  =/  mismatched=pack-boards:stead-team-owner  (malt ~[[project altered]])
  =/  empty-board=pack-boards:stead-team-owner
    (malt ~[[project (empty:stead-code-pack-review-board destination)]])
  =/  missing-result
    (mule |.((on-load:initial !>([%stead-home %9 team code [%open 1 ~] ~ anchors external *pack-boards:stead-team-owner]))))
  =/  absent-result
    (mule |.((on-load:initial !>([%stead-home %9 team code [%open 1 ~] ~ anchors external pending-boards]))))
  =/  mismatch-result
    (mule |.((on-load:initial !>([%stead-home %9 team code [%open 1 ~] ~ anchors external mismatched]))))
  =/  empty-result
    (mule |.((on-load:initial !>([%stead-home %9 team code [%open 1 ~] ~ anchors *external-writes:stead-team-owner empty-board]))))
  =/  orphan-result
    (mule |.((on-load:initial !>([%stead-home %9 team code [%open 1 ~] ~ anchors *external-writes:stead-team-owner boards]))))
  =/  ok=?
    ?&  ?=(%| -.missing-result)  ?=(%| -.absent-result)
        ?=(%| -.mismatch-result)  ?=(%| -.empty-result)
        ?=(%| -.orphan-result)
    ==
  (expect !>(ok))
++  test-home-v9-interleaved-raw-promotion-raw-history-roundtrips
  =/  raw-first=@t  '019939ba-4000-7000-8000-000000000040'
  =/  raw-last=@t  '019939ba-4000-7000-8000-000000000041'
  =/  start=manifest
    (seal current(refs (~(put by refs.current) source-key (oid-text:stead-git 0x11))))
  =/  genesis=entry:stead-code-pack-anchor
    [%accepted [start ~zod 1 900.001] [bootstrap who 2]]
  =/  first  (raw-advance (need (open genesis)) raw-first 1 0x11 0x22 current 3)
  =/  env=authority:stead-code-pack-review  env:review-fixture
  =/  proposed
    (submit:stead-code-pack-review-board (empty:stead-code-pack-review-board destination) env 1 current owner.reviewed '019939ba-4000-7000-8000-000000000014' source item.reviewed)
  ?>  ?=(%applied -.proposed)
  =/  row  (~(got by proposals.next.proposed) id.item.reviewed)
  =/  approved
    (approve:stead-code-pack-review-board next.proposed env 1 current reviewer.review.candidate.promotion '019939ba-4000-7000-8000-000000000015' row)
  ?>  ?=(%applied -.approved)
  =/  proof=checked  (evidence:stead-code-pack-promotion promotion)
  =/  merged
    (accept:stead-code-pack-review-board next.approved env 1 current merger.promotion request.promotion row proof(generation 1) ~)
  ?>  ?=(%applied -.merged)
  =/  promoted  (promote first saved.merged accepted-at.saved.merged)
  ?>  ?=(%& -.promoted)
  =/  last-pack=manifest
    (seal current.p.promoted(refs (~(put by refs.current.p.promoted) source-key (oid-text:stead-git 0x33))))
  =/  final  (raw-advance p.promoted raw-last 2 0x22 0x33 last-pack 103)
  =/  mixed-anchors=state:stead-code-pack-anchor  (malt ~[[project genesis]])
  =/  mixed-external=external-writes:stead-team-owner  (malt ~[[project final]])
  =/  mixed-boards=pack-boards:stead-team-owner  (malt ~[[project next.merged]])
  =/  restored
    (reload !>([%stead-home %9 team code [%open 1 ~] ~ mixed-anchors mixed-external mixed-boards]))
  =/  db  (~(got by external.row.restored) project)
  =/  ok=?
    ?&  (valid final genesis)
        =(mixed-anchors packs.row.restored)
        =(mixed-external external.row.restored)
        =(mixed-boards reviews.row.restored)
        =(3 generation.db)
        =(2 ~(wyt by receipts.db))
        =(1 ~(wyt by promotions.db))
        =(~[raw-last request.promotion raw-first] journal.db)
        =(last-pack current.db)
        =(105 last.db)
        =(~ pending.db)
    ==
  (expect !>(ok))
--
