/+  *test, stead-team, stead-team-config, stead-team-codec, stead-team-owner, stead-code-home, stead-home-handoff, stead-project-retirement, stead-projection, stead-codec, stead-code-pack-anchor, stead-code-pack-push, stead-code-pack-ledger, stead-code-receive, stead-session, stead-code-git-graph, stead-git
/=  home-agent  /app/stead-home
=,  stead-code-pack-ledger
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  destination=scope  [~zod project project 1]
=/  request=@t  '019939ba-4000-7000-8000-000000000004'
=/  bootstrap=@t  '019939ba-4000-7000-8000-000000000006'
=/  digest=@t  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
=/  main=@t  'refs/heads/main'
=/  tag=@t  'refs/tags/v1'
=/  exact-ref=@t  (cat 3 'refs/heads/topic-' 0xff)
=/  main-key  (bytes-hex:stead-codec main)
=/  tag-key  (bytes-hex:stead-codec tag)
=/  exact-key  '726566732f68656164732f746f7069632dff'
=/  seal
  |=  input=manifest
  ^-  manifest
  =/  raw  (snapshot-bytes:stead-code-pack-anchor input)
  =/  size  (met 3 raw)
  input(snapshot (hex:stead-codec 64 (sha-256l:sha [size (rev 3 size raw)])))
=/  current=manifest
  %-  seal
  :*  destination  ''  main-key
      (malt ~[[main-key (oid-text:stead-git 0x11)] [exact-key (oid-text:stead-git 0x11)]])
      digest  400  3  500  digest
  ==
=/  pack=manifest
  =/  refs=(map @t @t)
    (malt ~[[main-key (oid-text:stead-git 0x22)] [tag-key (oid-text:stead-git 0x33)] [exact-key (oid-text:stead-git 0x22)]])
  (seal current(refs refs, objects 6))
=/  kinds=(list [@ux object-kind:stead-code-git-graph])
  ~[[0x22 %commit] [0x33 %tag]]
=/  proof=checked
  :*  destination  snapshot.current  0  digest  request
      ~[[tag 0x0 0x33] [exact-ref 0x11 0x22] [main 0x11 0x22]]
      pack  (malt kinds)  (silt ~[[0x11 0x22]])
  ==
=/  allow-all=allow  |=([action:stead-code-receive update] &)
=/  deny-all=allow  |=([action:stead-code-receive update] |)
=/  who=actor
  [~bus '019939ba-4000-7000-8000-000000000002' '019939ba-4000-7000-8000-000000000003' 1 & 2.000.000]
=/  anchor=entry:stead-code-pack-anchor
  [%accepted [current ~zod 1 900.001] [bootstrap who 2]]
=/  db  (need (open anchor))
=/  claim=intent
  [destination snapshot.current 0 digest request 1 snapshot.pack changes.proof]
=/  company-init  (configure:stead-team empty:stead-team '{"protocol":"stead.team-config/1","expected_revision":"0","home":"~zod","origin":"https://home.test","organization_id":"019939ba-4000-7000-8000-000000000005","team_id":"019939ba-4000-7000-8000-000000000006","custody":"local-disposable","runtime":"isolated-fake","bindings":{"~bus":{"principal_id":"019939ba-4000-7000-8000-000000000002","binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"1","active":"yes","expires_at_ms":"2000000","display_name":"Synthetic member"}},"project_creators":{"019939ba-4000-7000-8000-000000000002":"yes"}}' ~zod 1)
=/  member  (need (native-context:stead-team company-init ~bus 1))
?>  =(identity.member who)
=/  create  (decode:stead-team-codec '{"protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000007","project_id":"019939ba-4000-7000-8000-000000000001","resource_id":"019939ba-4000-7000-8000-000000000001","expected_revision":"0","authority_epoch":"1","operation":"project.create","payload":{"organization_id":"019939ba-4000-7000-8000-000000000005","owning_team_id":"019939ba-4000-7000-8000-000000000006","title":"Synthetic ledger reload","project_key":"LEDGER","preset":"general"}}')
=/  created  (apply-command:stead-team company-init member create 1)
?>  =(1 (lent journal.data.next.created))
=/  company  next.created
=/  team=saved:stead-team-owner  [company *state:stead-projection]
=/  code=persisted:stead-code-home  *persisted:stead-code-home
=/  anchors=state:stead-code-pack-anchor  (malt ~[[project anchor]])
=/  context=bowl:gall  *bowl:gall
=.  context  context(our ~zod, src ~zod, now (add ~1970.1.1 (mul 2 ~s1)), eny `@uvJ`17, act 5)
=/  initial=agent:gall  ~(. home-agent context)
=/  staged  (admit db claim who 3 incarnation.claim allow-all ~)
?>  ?=(%applied -.staged)
=/  checked  (verify next.staged claim proof who 4 incarnation.claim allow-all ~)
?>  ?=(%applied -.checked)
=/  accepted  (commit next.checked claim proof who 5 incarnation.claim allow-all ~)
?>  ?=(%applied -.accepted)
=/  external=external-writes-v1:stead-team-owner  (malt ~[[project (as-v1 next.accepted)]])
=/  pending-external=external-writes-v1:stead-team-owner  (malt ~[[project (as-v1 next.checked)]])
=/  baseline=vase  !>([%stead-home %7 team code [%open 1 ~] ~ anchors])
=/  v8=vase  !>([%stead-home %8 team code [%open 1 ~] ~ anchors external])
=/  custody
  |=  saved=vase
  ?:  ?=([%stead-home %3 *] q.saved)  =/  stored  !<([%stead-home %3 db=* projection=*] saved)  (shax (jam db.stored))  ?:  ?=([%stead-home %4 *] q.saved)  =/  stored  !<([%stead-home %4 team=[db=* projection=*] code=*] saved)  (shax (jam [db.team.stored code.stored]))  ?:  ?=([%stead-home %5 *] q.saved)  =/  stored  !<([%stead-home %5 team=[db=* projection=*] code=*] saved)  (shax (jam [db.team.stored code.stored]))  ?:  ?=([%stead-home %6 *] q.saved)  =/  stored  !<([%stead-home %6 team=[db=* projection=*] code=* handoff=*] saved)  (shax (jam [db.team.stored code.stored handoff.stored]))  ?:  ?=([%stead-home %7 *] q.saved)  =/  stored  !<([%stead-home %7 team=[db=* projection=*] code=* handoff=* retired=* packs=*] saved)  (shax (jam [db.team.stored code.stored handoff.stored retired.stored packs.stored]))  ?>  ?=([%stead-home %8 *] q.saved)  =/  stored  !<([%stead-home %8 team=[db=* projection=*] code=* handoff=* retired=* packs=* external=*] saved)  (shax (jam [db.team.stored code.stored handoff.stored retired.stored packs.stored external.stored]))
|%
++  test-home-v8-v7-envelope-remains-v7
  =/  [cards=(list card:agent:gall) loaded=agent:gall]  (on-load:initial baseline)
  =/  saved=vase  on-save:loaded
  =/  restored  !<([%stead-home %7 team=saved:stead-team-owner code=persisted:stead-code-home mode=phase:stead-home-handoff retired=ledger:stead-project-retirement packs=state:stead-code-pack-anchor] saved)
  =/  ok=?
    ?&  ?=(^ cards)
        =(company db.team.restored)
        =(code code.restored)
        =(anchors packs.restored)
        =([%open 1 ~] mode.restored)
        =(~ retired.restored)
        =((custody baseline) (custody saved))
    ==
  (expect !>(ok))
++  test-home-v8-load-save-retains-exact-accepted-ledger
  =/  [cards=(list card:agent:gall) loaded=agent:gall]  (on-load:initial v8)
  =/  saved=vase  on-save:loaded
  =/  restored  !<([%stead-home %8 team=saved:stead-team-owner code=persisted:stead-code-home mode=phase:stead-home-handoff retired=ledger:stead-project-retirement packs=state:stead-code-pack-anchor external=external-writes-v1:stead-team-owner] saved)
  =/  row  (~(got by external.restored) project)
  =/  [again-cards=(list card:agent:gall) again=agent:gall]  (on-load:initial saved)
  =/  second=vase  on-save:again
  =/  ok=?
    ?&  ?=(^ cards)
        =(company db.team.restored)
        =(external external.restored)
        =(generation.row 1)
        =(current.row pack)
        =(~[request] journal.row)
        ?=(~ pending.row)
        =(q.saved q.second)
        =((custody v8) (custody saved))
        =((custody saved) (shax (jam [company code [%open 1 ~] ~ anchors external])))
    ==
  (expect !>(ok))
++  test-home-v8-pending-intent-survives-without-auto-commit
  =/  pending-vase=vase  !>([%stead-home %8 team code [%open 1 ~] ~ anchors pending-external])
  =/  [cards=(list card:agent:gall) loaded=agent:gall]  (on-load:initial pending-vase)
  =/  saved=vase  on-save:loaded
  =/  restored  !<([%stead-home %8 team=saved:stead-team-owner code=persisted:stead-code-home mode=phase:stead-home-handoff retired=ledger:stead-project-retirement packs=state:stead-code-pack-anchor external=external-writes-v1:stead-team-owner] saved)
  =/  row  (~(got by external.restored) project)
  =/  ok=?
    ?&  =(pending-external external.restored)
        =(current.row current)
        =(generation.row 0)
        ?=([~ %verified *] pending.row)
        ?=([%rejected %incarnation-conflict] (commit (from-v1 row) claim proof who 6 digest allow-all ~))
    ==
  (expect !>(ok))
++  test-home-v8-rejects-empty-or-invalid-ledger-and-future-state
  =/  empty-result  (mule |.((on-load:initial !>([%stead-home %8 team code [%open 1 ~] ~ anchors *external-writes-v1:stead-team-owner]))))
  =/  invalid=external-writes-v1:stead-team-owner  (malt ~[[project (as-v1 db(seed digest))]])
  =/  bad-result  (mule |.((on-load:initial !>([%stead-home %8 team code [%open 1 ~] ~ anchors invalid]))))
  =/  other=external-writes-v1:stead-team-owner  (malt ~[[request (as-v1 next.accepted)]])
  =/  scope-result  (mule |.((on-load:initial !>([%stead-home %8 team code [%open 1 ~] ~ anchors other]))))
  =/  future-result  (mule |.((on-load:initial !>([%stead-home %10 team code [%open 1 ~] ~ anchors external]))))
  (expect !>(?&(?=(%| -.empty-result) ?=(%| -.bad-result) ?=(%| -.scope-result) ?=(%| -.future-result))))
++  test-home-v8-custody-omits-projection-but-binds-external-ledger
  =/  changed-view=state:stead-projection  *state:stead-projection
  =/  different-team  team(projection changed-view(poisoned &))
  =/  changed-projection=vase  !>([%stead-home %8 different-team code [%open 1 ~] ~ anchors external])
  =/  changed-ledger=vase  !>([%stead-home %8 team code [%open 1 ~] ~ anchors pending-external])
  (expect !>(&(=((custody v8) (custody changed-projection)) !=((custody v8) (custody changed-ledger)))))
--
