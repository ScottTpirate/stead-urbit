::  Explicit transient relay state. Restart and bootstrap clear all pins.
::  The operator installs the exact Home incarnation and repository target.
/+  stead-codec, stead-session, stead-code-credentials, stead-code-pack-anchor, stead-code-pack-worker-signature
|%
+$  scope  scope:stead-code-credentials
+$  worker  pin:stead-code-pack-worker-signature
+$  policy  [destination=scope incarnation=@t key=worker relay-proof=@t]
+$  state
  $%  [%closed generation=@ud ~]
      [%open generation=@ud installed=policy]
  ==
+$  command
  $%  [%close expected=@ud ~]
      [%open expected=@ud desired=policy]
  ==
++  reset
  |=  gate=state
  ^-  state
  [%closed generation.gate ~]
++  fingerprint
  |=  supplied=@t
  (digest:stead-session 'stead.git-pack-relay-capability/1' supplied)
++  matches
  |=  [gate=state selected=scope incarnation=@t]
  ^-  ?
  ?.  ?=(%open -.gate)  |
  ?&  (token-valid:stead-session incarnation)
      =(selected destination.installed.gate)
      =(incarnation incarnation.installed.gate)
  ==
++  current-key
  |=  [gate=state selected=scope incarnation=@t]
  ^-  (unit worker)
  ?.  &(?=(%open -.gate) (matches gate selected incarnation))  ~
  [~ key.installed.gate]
++  allowed
  |=  [gate=state selected=scope incarnation=@t supplied=@t]
  ^-  (unit worker)
  ?.  ?&  ?=(%open -.gate)  (matches gate selected incarnation)
          (token-valid:stead-session supplied)
          =(relay-proof.installed.gate (fingerprint supplied))
      ==
    ~
  [~ key.installed.gate]
++  transition
  |=  [gate=state current=scope incarnation=@t cmd=command]
  ^-  (unit state)
  ?.  ?&  (lth generation.gate 18.446.744.073.709.551.615)
          =(generation.gate expected.cmd)
      ==
    ~
  =/  serial  +(generation.gate)
  ?:  ?=(%close -.cmd)  [~ %closed serial ~]
  =/  proposed  desired.cmd
  ?.  ?&  ?=(%closed -.gate)
          (scope-valid:stead-code-credentials current)
          =(destination.proposed current)
          (token-valid:stead-session incarnation)
          =(incarnation.proposed incarnation)
          (generation-valid:stead-code-pack-worker-signature generation.key.proposed)
          (gth generation.key.proposed generation.gate)
          (hex-text:stead-code-pack-anchor public.key.proposed 64)
          (token-valid:stead-session relay-proof.proposed)
      ==
    ~
  [~ %open generation.key.proposed proposed]
--
