::  Real Gall load/save/event arms on synthetic bowls in the disposable fake.
::  This is not a cross-ship, HTTP, cold-restart or real-ship custody proof.
/+  *test, stead-codec, stead-team, stead-team-owner, stead-projection, stead-product-home, stead-product-history, stead-code-home, stead-home-handoff, stead-project-retirement, stead-code-pack-anchor, stead-code-pack-ledger
/=  home-agent  /app/stead-home
/=  fixture  /tests/stead-product-doc-history
=,  stead-codec
=/  context=bowl:gall  *bowl:gall
=.  context  context(our ~zod, src ~zod, now ~2026.11.15, eny `@uvJ`17, act 5)
=/  initial=agent:gall  ~(. home-agent context)
=/  source=target:stead-product-home  [%predecessor next.private-box:fixture]
=/  finished=target:stead-product-home  [%product baseline:fixture]
=/  accepted=target:stead-product-home  [%product next.completed:fixture]
|%
+$  envelope
  $:  %stead-home  %10  profile=@t  target=target:stead-product-home
      code=persisted:stead-code-home  mode=phase:stead-home-handoff
      retired=ledger:stead-project-retirement  packs=state:stead-code-pack-anchor
      external=external-writes:stead-team-owner  reviews=pack-boards:stead-team-owner
  ==
++  saved
  |=  target=target:stead-product-home
  ^-  vase
  !>  [%stead-home %10 profile:stead-product-home target *persisted:stead-code-home [%open 1 ~] *ledger:stead-project-retirement *state:stead-code-pack-anchor *external-writes:stead-team-owner *pack-boards:stead-team-owner]
++  waits
  |=  cards=(list card:agent:gall)
  ^-  (list wire)
  %+  murn  cards
  |=  item=card:agent:gall
  ?.  ?=([%pass [%stead-rebuild @ ~] %arvo %b %wait *] item)  ~
  =/  [%pass route=wire %arvo %b %wait when=@da]  item
  (some route)
++  finish
  |=  [cards=(list card:agent:gall) actor=agent:gall]
  ^-  agent:gall
  =/  budget=@ud  1.024
  |-
  =/  pending  (waits cards)
  ?~  pending  actor
  ?>  &((gth budget 0) =(1 (lent pending)))
  =/  [more=(list card:agent:gall) next=agent:gall]
    (on-arvo:actor i.pending [%behn %wake ~])
  $(cards more, actor next, budget (dec budget))
++  published
  ::  This actual owner watch is unavailable until product validation publishes.
  ::  A failed restore also stops emitting wakes, so quiescence alone is no proof.
  |=  actor=agent:gall
  ^-  ?
  =/  route=path  [%product-owner-receipt (id:fixture 999) (hex 64 0) ~]
  =/  observed  (mule |.((on-watch:actor route)))
  ?:  ?=(%| -.observed)  |
  =/  [cards=(list card:agent:gall) next=agent:gall]  p.observed
  =(2 (lent cards))
++  legacy
  ^-  vase
  !>  [%stead-home %3 [next.private-box:fixture *state:stead-projection]]
++  activation
  ^-  @t
  %-  canonical
  %-  object
  :~  ['protocol' 'stead.product-activate/1']
      ['profile' profile:stead-product-home]
      ['expected_config_revision' '1']
      ['predecessor_sha256' (hash 'stead.product-predecessor/1' (bytes-hex (jam next.private-box:fixture)))]
  ==
++  test-home-v10-predecessor-save-is-pristine-before-migration
  =/  original  (saved source)
  =/  [cards=(list card:agent:gall) loaded=agent:gall]  (on-load:initial original)
  =/  immediate=vase  on-save:loaded
  =/  pending  (waits cards)
  ?>  ?=(^ pending)
  =/  [next-cards=(list card:agent:gall) advanced=agent:gall]
    (on-arvo:loaded i.pending [%behn %wake ~])
  =/  partial=vase  on-save:advanced
  =/  row  !<(envelope partial)
  =/  [again-cards=(list card:agent:gall) again=agent:gall]  (on-load:initial partial)
  =/  first  (finish next-cards advanced)
  =/  second  (finish again-cards again)
  =/  first-save=vase  on-save:first
  =/  second-save=vase  on-save:second
  =/  final  !<(envelope first-save)
  %-  expect
  !>  ?&  =(q.original q.immediate)
          =(source target.row)
          =(finished target.final)  (published first)  (published second)
          =(q.first-save q.second-save)
          =(profile:stead-product-home profile.final)
      ==
++  test-home-v10-product-restore-retains-full-target-before-publish
  =/  original  (saved accepted)
  =/  [cards=(list card:agent:gall) loaded=agent:gall]  (on-load:initial original)
  =/  immediate=vase  on-save:loaded
  =/  final  (finish cards loaded)
  =/  output=vase  on-save:final
  =/  row  !<(envelope output)
  =/  [again-cards=(list card:agent:gall) again=agent:gall]  (on-load:initial output)
  =/  replayed  (finish again-cards again)
  =/  replayed-save=vase  on-save:replayed
  %-  expect
  !>  ?&  =(q.original q.immediate)
          =(q.original q.output)
          =(q.output q.replayed-save)
          =(accepted target.row)  (published final)  (published replayed)
          =([%open 1 ~] mode.row)
          =(*persisted:stead-code-home code.row)
      ==
++  test-home-v10-wrong-restore-wake-cannot-publish-or-alter-target
  =/  original  (saved accepted)
  =/  [cards=(list card:agent:gall) loaded=agent:gall]  (on-load:initial original)
  =/  [ignored=(list card:agent:gall) next=agent:gall]
    (on-arvo:loaded /stead-rebuild/not-the-current-job [%behn %wake ~])
  =/  before=vase  on-save:loaded
  =/  after=vase  on-save:next
  %-  expect
  !>  ?&  ?=(~ ignored)
          =(q.original q.after)
          =(q.before q.after)
      ==
++  test-home-v10-predecessor-never-activates-without-owner-control
  =/  [cards=(list card:agent:gall) loaded=agent:gall]  (on-load:initial legacy)
  =/  first=vase  on-save:loaded
  =/  final  (finish cards loaded)
  =/  last=vase  on-save:final
  =/  old  !<([%stead-home %3 team=saved:stead-team-owner] last)
  %-  expect
  !>  ?&  ?=([%stead-home %3 *] q.first)
          ?=([%stead-home %3 *] q.last)
          =(next.private-box:fixture db.team.old)
      ==
++  test-home-v10-activation-requires-actual-owner-and-exact-prefix
  =/  remote=agent:gall  ~(. home-agent context(src ~bus))
  =/  [remote-cards=(list card:agent:gall) remote-loaded=agent:gall]  (on-load:remote legacy)
  =/  remote-ready  (finish remote-cards remote-loaded)
  =/  denied  (mule |.((on-poke:remote-ready %stead-product-activate-1 !>(activation))))
  =/  [cards=(list card:agent:gall) loaded=agent:gall]  (on-load:initial legacy)
  =/  ready  (finish cards loaded)
  =/  value  (need (parse activation))
  ?>  ?=([%o *] value)
  =/  changed  (canonical [%o (~(put by p.value) 'predecessor_sha256' [%s (hex 64 0)])])
  =/  stale  (mule |.((on-poke:ready %stead-product-activate-1 !>(changed))))
  =/  [activated-cards=(list card:agent:gall) activated=agent:gall]
    (on-poke:ready %stead-product-activate-1 !>(activation))
  =/  started  !<(envelope on-save:activated)
  =/  result  (finish activated-cards activated)
  =/  target  !<(envelope on-save:result)
  %-  expect
  !>  ?&  ?=(%| -.denied)  ?=(%| -.stale)
          =(source target.started)
          =(finished target.target)  (published result)
      ==
++  test-home-v10-rejects-wrong-profile-code-and-future-envelope
  =/  row  !<(envelope (saved accepted))
  =/  wrong-profile  (mule |.((on-load:initial !>(row(profile 'anything-else')))))
  =/  occupied  row(external (~(put by external.row) (id:fixture 100) *ledger:stead-code-pack-ledger))
  =/  code-present  (mule |.((on-load:initial !>(occupied))))
  =/  future  (mule |.((on-load:initial !>([%stead-home %11 accepted]))))
  %-  expect
  !>  ?&  ?=(%| -.wrong-profile)
          ?=(%| -.code-present)
          ?=(%| -.future)
      ==
--
