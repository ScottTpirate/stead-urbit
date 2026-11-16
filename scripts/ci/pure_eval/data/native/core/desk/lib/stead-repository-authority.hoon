::  PRIVATE current-human repository authority. No transport/save allocation.
::  Home supplies one admitted synchronous snapshot. Reconstruct it for every
::  later event/final write; these closures are never saved or queued. Browser
::  secrets are transient inputs only, never catalog/history/receipt fields.
/+  stead-codec, stead-team, stead-principals, stead-actor, stead-session, stead-project-retirement, stead-repository-catalog, stead-code-credentials
=,  stead-codec
|%
+$  snapshot
  $:  home=@p  db=state:stead-team  principals=state:stead-principals
      repositories=catalog:stead-repository-catalog
      retired=ledger:stead-project-retirement  sessions=state:stead-session
  ==
+$  source  $%([%native sender=@p] [%browser cookie=@t csrf=@t])
+$  ref  ref:stead-repository-catalog
+$  access  access:stead-repository-catalog
+$  resolved  resolved:stead-repository-catalog
++  valid
  ::  Defensive closure, not a substitute for authentic Home restore/history.
  |=  [state=snapshot now=@ud]
  ^-  ?
  =/  attempted
    %-  mule
    |.
    ?>  ?&  (gth now 0)  (lte now 18.446.744.073.709.551.615)
            initialized.data.db.state
            (lte (met 0 home.state) 128)  ?=(^ current.registry.db.state)
        ==
    ?&  =(home.state home.u.current.registry.db.state)
        (valid:stead-repository-catalog repositories.state)
        (validate:stead-project-retirement home.state data.db.state retired.state)
    ==
  ?:  ?=(%| -.attempted)  |
  p.attempted
++  human
  |=  [state=snapshot actor=verified:stead-actor now=@ud]
  ^-  (unit authentication:stead-team)
  ?.  (valid state now)  ~
  ?.  ?=(%native -.actor)  ~
  ?.  &(=(home.state home.context.actor) (native-human:stead-actor db.state principals.state actor now))  ~
  (some context.actor)
++  native
  |=  [state=snapshot sender=@p now=@ud]
  ^-  (unit authentication:stead-team)
  ?.  (valid state now)  ~
  =/  context  (native-context:stead-team db.state sender now)
  ?~  context  ~
  =/  actor  (verify-native:stead-actor db.state principals.state u.context now)
  ?~  actor  ~
  (human state u.actor now)
++  browser
  ::  Actual Eyre TLS/Host/Origin checks remain the authoritative caller's job.
  ::  Current ledger possession is required, not a cached authentication noun.
  |=  [state=snapshot cookie=@t csrf=@t now=@ud]
  ^-  (unit authentication:stead-team)
  ?.  ?&  (valid state now)  (token-valid:stead-session cookie)
          (token-valid:stead-session csrf)
      ==
    ~
  =/  saved  (~(get by sessions.sessions.state) (digest:stead-session 'stead.session/1' cookie))
  ?~  saved  ~
  =/  identity  (native state ship.identity.u.saved now)
  ?~  identity  ~
  =/  config  (need current.registry.db.state)
  =/  authorized
    (authorize:stead-session sessions.state cookie csrf identity.u.identity home.state origin.config now)
  ?~  authorized  ~
  =/  context  (browser-context:stead-team db.state u.authorized now)
  ?~  context  ~
  =/  actor  (verify-native:stead-actor db.state principals.state u.context now)
  ?~  actor  ~
  (human state u.actor now)
++  authenticate
  |=  [state=snapshot source=source now=@ud]
  ^-  (unit authentication:stead-team)
  ?-  -.source
    %native  (native state sender.source now)
    %browser  (browser state cookie.source csrf.source now)
  ==
++  current
  |=  [state=snapshot source=source]
  ^-  current:stead-repository-catalog
  |=  [who=actor:stead-session project=@t now=@ud]
  ^-  (unit facts:stead-repository-catalog)
  =/  context  (authenticate state source now)
  ?~  context  ~
  ?.  &(=(who identity.u.context) (uuid project))  ~
  =/  row  (~(get by projects.data.db.state) project)
  ?~  row  ~
  =/  rank  (role:stead-team db.state u.context project now)
  ?.  ?&  (gth rank 0)  (lte rank 3)
          (gth epoch.u.row 0)  (lte epoch.u.row 18.446.744.073.709.551.615)
      ==
    ~
  (some [home.state epoch.u.row rank (~(has by retired.state) project)])
++  resolve
  |=  [state=snapshot source=source target=ref operation=access now=@ud]
  ^-  (unit resolved)
  =/  context  (authenticate state source now)
  ?~  context  ~
  (resolve:stead-repository-catalog repositories.state target identity.u.context operation now (current state source))
++  legacy-resolve
  |=  [state=snapshot source=source project=@t operation=access now=@ud]
  ^-  (unit resolved)
  =/  context  (authenticate state source now)
  ?~  context  ~
  (legacy-resolve:stead-repository-catalog repositories.state project identity.u.context operation now (current state source))
++  create
  |=  [state=snapshot source=source raw=@t now=@ud]
  ^-  decision:stead-repository-catalog
  =/  context  (authenticate state source now)
  ?~  context  [%denied %denied-or-not-found]
  (create:stead-repository-catalog repositories.state raw identity.u.context now (current state source))
++  member
  |=  [state=snapshot now=@ud]
  ^-  membership:stead-code-credentials
  |=  sender=@p
  ^-  (unit actor:stead-session)
  =/  context  (native state sender now)
  ?~  context  ~
  (some identity.u.context)
++  allowed
  |=  [state=snapshot now=@ud]
  ^-  allowance:stead-code-credentials
  |=  [who=actor:stead-session destination=scope:stead-code-credentials operation=access:stead-code-credentials]
  ^-  ?
  =/  context  (native state ship.who now)
  ?~  context  |
  ?.  =(who identity.u.context)  |
  =/  found  (resolve state [%native ship.who] [project.destination repository.destination] operation now)
  ?~  found  |
  =(destination destination.u.found)
++  issue
  |=  $:  state=snapshot  book=ledger:stead-code-credentials  source=source
          target=ref  writable=?  now=@ud  entropy=@
      ==
  ^-  issue-result:stead-code-credentials
  =/  context  (authenticate state source now)
  ?~  context  [%| %denied]
  =/  found  (resolve state source target ?:(writable %write %read) now)
  ?~  found  [%| %denied]
  (issue:stead-code-credentials book identity.u.context destination.u.found writable expires.u.context now entropy (allowed state now))
++  check
  |=  $:  state=snapshot  book=ledger:stead-code-credentials  bearer=@t
          destination=scope:stead-code-credentials  operation=access:stead-code-credentials  now=@ud
      ==
  ^-  (unit actor:stead-session)
  ?.  (valid state now)  ~
  (check:stead-code-credentials book bearer destination operation now (member state now) (allowed state now))
--
