::  PRIVATE single-shared-doc/1 structural materialization. No actor, current
::  authority, settlement, transport, Home route or saved-state activation.
::  The private JSON subset exists only for this fixed request profile. It
::  does not widen stead-codec; raw response normalization remains separate.
/+  stead-codec, stead-run-state, stead-run-codec
=,  stead-codec
|%
+$  octets  [length=@ud data=@]
+$  connection
  [bytes=@t digest=@t id=@t revision=@ud model=@t limits=usage:stead-run-state input-tokens=@ud output-tokens=@ud]
+$  material
  [bytes=@t policy=@t connection=connection scope=object-map context=@t registry=@t request=@t intent=intent:stead-run-state]
++  sha256
  |=  raw=octets
  ^-  @t
  ?>  &((lte length.raw 65.536) (lte (met 3 data.raw) length.raw))
  (hex 64 (sha-256l:sha [length.raw (rev 3 length.raw data.raw)]))
++  text-sha256
  |=  raw=@t
  (sha256 [(met 3 raw) raw])
++  nesting
  ::  Limit syntactic depth BEFORE the recursive JSON parser sees bytes.
  ::  Quote/backslash tracking ignores bracket text inside JSON strings.
  |=  raw=@t
  ^-  ?
  =/  pending=(list @)  (rip 3 raw)
  =/  depth=@ud  0
  =/  quoted=?  |
  =/  escaped=?  |
  |-  ^-  ?
  ?~  pending  &(!quoted !escaped =(0 depth))
  =/  byte  i.pending
  ?:  quoted
    ?:  escaped  $(pending t.pending, escaped |)
    ?:  =(92 byte)  $(pending t.pending, escaped &)
    ?:  =(34 byte)  $(pending t.pending, quoted |)
    $(pending t.pending)
  ?:  =(34 byte)  $(pending t.pending, quoted &)
  ?:  ?|(=(123 byte) =(91 byte))
    &((lth depth 8) $(pending t.pending, depth +(depth)))
  ?:  ?|(=(125 byte) =(93 byte))
    &((gth depth 0) $(pending t.pending, depth (dec depth)))
  $(pending t.pending)
++  json-rule
  %+  knee  *json
  |.  ~+
  %+  ifix  [spac:de:json:html spac:de:json:html]
  ;~  pose
    (cold ~ (jest 'null'))
    (stag %b bool:de:json:html)
    (stag %s string-rule)
    (cook |=(s=tape [%n p=(rap 3 s)]) numb:de:json:html)
    (stag %o (dict-rule json-rule))
    %+  stag  %a
    %+  sear
      |=  rows=(list json)
      ^-  (unit (list json))
      ?:((lte (lent rows) 32) (some rows) ~)
    (ifix [sel (wish:de:json:html ser)] (more (wish:de:json:html com) json-rule))
  ==
++  encode
  |=  value=json
  ^-  @t
  ?~  value  'null'
  ?-  -.value
    %s  (quote p.value)
    %b  ?:(p.value 'true' 'false')
    %n
      =/  number  (uint p.value)
      ?>  (lte number 9.007.199.254.740.991)
      (decimal number)
    %a
      (cat 3 '[' (cat 3 (joined (turn p.value encode)) ']'))
    %o
      =/  pairs=(list [@t json])
        (sort ~(tap by p.value) |=([a=[@t json] b=[@t json]] (aor -.a -.b)))
      =/  parts=(list @t)
        %+  turn  pairs
        |=  row=[key=@t value=json]
        (cat 3 (quote key.row) (cat 3 ':' (encode value.row)))
      (cat 3 '{' (cat 3 (joined parts) '}'))
  ==
++  joined
  |=  rows=(list @t)
  ^-  @t
  ?~  rows  ''
  =/  out=@t  i.rows
  =/  pending=(list @t)  t.rows
  |-  ^-  @t
  ?~  pending  out
  $(pending t.pending, out (cat 3 out (cat 3 ',' i.pending)))
++  parsed
  |=  [raw=@t maximum=@ud]
  ^-  json
  ?>  &((gth (met 3 raw) 0) (lte (met 3 raw) (min maximum 65.536)) (nesting raw))
  =/  value=json  (need (rush raw json-rule))
  ?>  =(raw (encode value))
  value
++  obj
  |=  value=json
  ^-  object-map
  ?>  ?=([%o *] value)
  p.value
++  closed
  |=  [value=json names=(list @t)]
  ^-  object-map
  =/  rows  (obj value)
  ?>  (keys rows names)
  rows
++  strings
  |=  [value=json names=(list @t)]
  ^-  object-map
  =/  rows  (closed value names)
  ?>  (levy ~(tap by rows) |=([key=@t val=json] ?=([%s *] val)))
  rows
++  child
  |=  [rows=object-map key=@t]
  ^-  json
  (~(got by rows) key)
++  positive
  |=  raw=@t
  ^-  @ud
  (positive:stead-run-codec raw)
++  digest
  |=  raw=@t
  ^-  @t
  (digest:stead-run-codec raw)
++  identity
  |=  raw=@t
  ^-  @t
  (identity:stead-run-codec raw)
++  label
  |=  [raw=@t maximum=@ud]
  ^-  @t
  ?>  ?&  (gth (met 3 raw) 0)  (lte (met 3 raw) maximum)
          (levy (rip 3 raw) |=(c=@ &((gte c 32) !=(c 127))))
      ==
  raw
++  usage
  |=  value=json
  ^-  usage:stead-run-state
  (usage-of:stead-run-codec (encode value))
++  within
  |=  [used=usage:stead-run-state maximum=usage:stead-run-state]
  ^-  ?
  ?&  (lte tools.used tools.maximum)  (lte network.used network.maximum)
      (lte tokens.used tokens.maximum)  (lte cost.used cost.maximum)
      (lte input.used input.maximum)  (lte output.used output.maximum)
  ==
++  endpoint
  ::  First native adapter supports this exact local loopback route only.
  ::  This shape is not actual namespace, egress, TLS or connection authority.
  |=  value=json
  ^-  @t
  =/  rows  (strings value ~['url' 'placement' 'egress_policy_digest'])
  ?>  =('local-isolated' (field rows 'placement'))
  =/  ignored  (digest (field rows 'egress_policy_digest'))
  =/  raw  (field rows 'url')
  =/  prefix  'http://127.0.0.1:'
  =/  suffix  '/v1/chat/completions'
  =/  start  (met 3 prefix)
  =/  end  (met 3 suffix)
  ?>  &((gth (met 3 raw) (add start end)) (lte (met 3 raw) 2.048))
  =/  length  (sub (met 3 raw) (add start end))
  =/  port  (positive (cut 3 [start length] raw))
  ?>  ?&  (lte port 65.535)  =(prefix (cut 3 [0 start] raw))
          =(suffix (cut 3 [(add start length) end] raw))
      ==
  raw
++  connection-of
  |=  raw=@t
  ^-  connection
  =/  rows
    (closed (parsed raw 8.192) ~['protocol' 'connection_id' 'revision' 'display_name' 'adapter' 'endpoint' 'model' 'authentication' 'capabilities' 'limits'])
  ?>  &(=('stead.model-connection/1' (field rows 'protocol')) =('llamacpp.chat-completions/1' (field rows 'adapter')))
  =/  name  (label (field rows 'display_name') 200)
  =/  model  (label (field rows 'model') 200)
  =/  destination  (endpoint (child rows 'endpoint'))
  =/  auth  (strings (child rows 'authentication') ~['kind'])
  ?>  =('none' (field auth 'kind'))
  =/  caps  (strings (child rows 'capabilities') ~['instruction_role' 'function_tools' 'token_limit_field' 'strict_tools' 'parallel_tool_calls' 'store'])
  ?>  ?&  =('system' (field caps 'instruction_role'))
          =('json-schema-strings/1' (field caps 'function_tools'))
          =('max_tokens' (field caps 'token_limit_field'))
          =('unsupported' (field caps 'strict_tools'))
          =('supported' (field caps 'parallel_tool_calls'))
          =('unsupported' (field caps 'store'))
      ==
  =/  limits
    (strings (child rows 'limits') ~['input_bytes' 'output_bytes' 'turns' 'tool_calls' 'request_timeout_ms' 'duration_ms' 'input_tokens' 'output_tokens' 'total_tokens' 'cost_units' 'billable_micro_usd'])
  =/  duration  (positive (field limits 'duration_ms'))
  =/  timeout  (positive (field limits 'request_timeout_ms'))
  =/  input-tokens  (positive (field limits 'input_tokens'))
  =/  output-tokens  (positive (field limits 'output_tokens'))
  =/  total-tokens  (positive (field limits 'total_tokens'))
  =/  ceiling=usage:stead-run-state
    [1 1 total-tokens (positive (field limits 'cost_units')) (positive (field limits 'input_bytes')) (positive (field limits 'output_bytes'))]
  ?>  ?&  =('1' (field limits 'turns'))  =('1' (field limits 'tool_calls'))
          =('0' (field limits 'billable_micro_usd'))
          (lte timeout duration)  (lte timeout 60.000)  (lte duration 600.000)
          (lte input-tokens 131.072)  (lte output-tokens 32.768)
          (lte total-tokens 262.144)  (lte cost.ceiling 1.000.000.000)
          (lte (add input-tokens output-tokens) total-tokens)
          (usage-valid:stead-run-state ceiling)
      ==
  [raw (hash 'stead.model-connection/1' raw) (identity (field rows 'connection_id')) (positive (field rows 'revision')) model ceiling input-tokens output-tokens]
++  policy-of
  ::  This validates only materialization/hash consistency. An actual historic
  ::  owner declaration and current head must be resolved by the future adapter.
  |=  [raw=@t connection=connection registry=@t scope=object-map]
  ^-  @t
  =/  rows  (closed (parsed raw 8.192) ~['protocol' 'home' 'agent_principal_id' 'runtime_id' 'runtime_revision' 'connections' 'request_profile'])
  ?>  ?&  =('stead.runtime-model-policy/1' (field rows 'protocol'))
          =('single-shared-doc/1' (field rows 'request_profile'))
          =((field rows 'home') (field scope 'home'))
          =((field rows 'runtime_id') (field scope 'runtime_id'))
          =((field rows 'runtime_revision') (field scope 'runtime_revision'))
      ==
  =/  principal  (identity (field rows 'agent_principal_id'))
  =/  connections  (obj (child rows 'connections'))
  ?>  &((gth ~(wyt by connections) 0) (lte ~(wyt by connections) 8))
  ?>  %+  levy  ~(tap by connections)
      |=  [id=@t val=json]
      ^-  ?
      ?>  (uuid id)
      =/  row  (closed val ~['revision' 'connection_digest' 'approved_tool_registry_digest' 'maximum_charge'])
      =/  revision  (positive (field row 'revision'))
      =/  connection-pin  (digest (field row 'connection_digest'))
      =/  tool-digest  (digest (field row 'approved_tool_registry_digest'))
      =/  maximum  (usage (child row 'maximum_charge'))
      &((gth tools.maximum 0) (gth network.maximum 0) (gth tokens.maximum 0) (gth cost.maximum 0))
  =/  selected  (obj (~(got by connections) id.connection))
  ?>  ?&  =(revision.connection (positive (field selected 'revision')))
          =(digest.connection (field selected 'connection_digest'))
          =((hash 'stead.tool-registry/1' registry) (field selected 'approved_tool_registry_digest'))
      ==
  (hash 'stead.runtime-model-policy/1' raw)
++  scope-of
  |=  raw=@t
  ^-  object-map
  =/  rows
    (strings (parsed raw 8.192) ~['home' 'project_id' 'run_id' 'attempt' 'effect_sequence' 'run_contract_sha256' 'context_digest' 'definition_id' 'definition_revision' 'runtime_id' 'runtime_revision' 'runtime_policy_digest' 'connection_digest'])
  =/  home  (need (slaw %p (field rows 'home')))
  ?>  &(=((scot %p home) (field rows 'home')) (lte (met 0 home) 128))
  =/  ids=(list @t)  ~['project_id' 'run_id' 'definition_id' 'runtime_id']
  ?>  (levy ids |=(key=@t (uuid (field rows key))))
  =/  digests=(list @t)  ~['run_contract_sha256' 'context_digest' 'runtime_policy_digest' 'connection_digest']
  ?>  (levy digests |=(key=@t (digest-valid:stead-run-state (field rows key))))
  =/  attempt  (positive (field rows 'attempt'))
  =/  definition  (positive (field rows 'definition_revision'))
  =/  runtime  (positive (field rows 'runtime_revision'))
  ?>  &((lte attempt 3) =('1' (field rows 'effect_sequence')))
  rows
++  registry-of
  |=  raw=@t
  ^-  object-map
  =/  value=json  (parsed raw 32.768)
  ?>  ?=([%a *] value)
  ?>  ?=(^ p.value)
  ?>  ?=(~ t.p.value)
  =/  tool  (closed i.p.value ~['tool_id' 'revision' 'name' 'description' 'arguments'])
  =/  id  (identity (field tool 'tool_id'))
  ?>  &(=('1' (field tool 'revision')) =('propose_doc_update' (field tool 'name')))
  =/  description  (label (field tool 'description') 1.024)
  =/  arguments  (strings (child tool 'arguments') ~['markdown'])
  ?>  =('8192' (field arguments 'markdown'))
  tool
++  context-of
  ::  Association is structural here; Home must still rebuild these bytes from
  ::  actual current readable shared Docs before accepting an effect.
  |=  [raw=@t scope=object-map instructions=@t policy=@t]
  ^-  @t
  =/  rows
    (strings (parsed raw 65.536) ~['protocol' 'project_id' 'work_id' 'execution_contract_revision' 'execution_contract_digest' 'title' 'description' 'acceptance_criteria' 'instructions_digest' 'runtime_policy_digest' 'documents'])
  ?>  ?&  =('stead.run-context/1' (field rows 'protocol'))
          =((field scope 'project_id') (field rows 'project_id'))
          =((text-sha256 instructions) (field rows 'instructions_digest'))
          =(policy (field rows 'runtime_policy_digest'))
          =((hash 'stead.run-context/1' raw) (field scope 'context_digest'))
          (title (field rows 'title'))
          (prose (field rows 'description') 32.768)
          (prose (field rows 'acceptance_criteria') 32.768)
      ==
  =/  work  (identity (field rows 'work_id'))
  =/  revision  (positive (field rows 'execution_contract_revision'))
  =/  contract  (digest (field rows 'execution_contract_digest'))
  =/  documents  (obj (parsed (field rows 'documents') 65.536))
  ?>  =(1 ~(wyt by documents))
  =/  entries=(list [@t json])  ~(tap by documents)
  ?>  ?=(^ entries)
  ::  The map key is required outcome identity, intentionally distinct from
  ::  target.document_id (stead-run-adapters.context-checked). Current Run
  ::  target/context equality remains an authority-adapter responsibility.
  ?>  (uuid -.i.entries)
  =/  document  (strings +.i.entries ~['target' 'markdown'])
  =/  target
    (strings (parsed (field document 'target') 8.192) ~['kind' 'project_id' 'collection_id' 'document_id' 'expected_revision' 'base_markdown_sha256'])
  ?>  &(=('document' (field target 'kind')) =((field scope 'project_id') (field target 'project_id')))
  =/  collection  (identity (field target 'collection_id'))
  =/  id  (identity (field target 'document_id'))
  =/  base  (uint (field target 'expected_revision'))
  =/  markdown  (field document 'markdown')
  ?>  (prose markdown 32.768)
  ?>  ?:  =(0 base)
        &(=('' markdown) =('' (field target 'base_markdown_sha256')))
      =((text-sha256 markdown) (field target 'base_markdown_sha256'))
  raw
++  request-body
  |=  [connection=connection instructions=@t context=@t tool=object-map]
  ^-  @t
  =/  markdown=json
    [%o (malt ~[['type' [%s 'string']] ['maxLength' [%n '8192']]])]
  =/  properties=json  [%o (malt ~[['markdown' markdown]])]
  =/  schema=json
    [%o (malt ~[['type' [%s 'object']] ['properties' properties] ['required' [%a ~[[%s 'markdown']]]] ['additionalProperties' [%b |]]])]
  =/  function=json
    [%o (malt ~[['name' [%s 'propose_doc_update']] ['description' [%s (field tool 'description')]] ['parameters' schema]])]
  =/  tool-value=json  [%o (malt ~[['type' [%s 'function']] ['function' function]])]
  =/  messages=(list json)
    ~[(object ~[['role' 'system'] ['content' instructions]]) (object ~[['role' 'user'] ['content' context]])]
  =/  fields=(list [@t json])
    :~  ['model' [%s model.connection]]  ['messages' [%a messages]]
        ['stream' [%b |]]  ['n' [%n '1']]
        ['max_tokens' [%n (decimal output-tokens.connection)]]
        ['tools' [%a ~[tool-value]]]  ['tool_choice' [%s 'auto']]
        ['parallel_tool_calls' [%b |]]
    ==
  (encode [%o (malt fields)])
++  nibble
  |=  char=@
  ^-  @ud
  ?:  &((gte char '0') (lte char '9'))  (sub char '0')
  ?>  &((gte char 'a') (lte char 'f'))
  (add 10 (sub char 'a'))
++  id-from-seed
  |=  [parent=@t seed=@t]
  ^-  @t
  ?>  &((uuid parent) (digest-valid:stead-run-state seed))
  =/  variant  (cut 3 [(add 8 (mod (nibble (cut 3 [16 1] seed)) 4)) 1] '0123456789abcdef')
  =/  id
    (rap 3 ~[(cut 3 [0 14] parent) '7' (cut 3 [13 3] seed) '-' variant (cut 3 [17 3] seed) '-' (cut 3 [20 12] seed)])
  ?>  (uuid id)
  id
++  effect-id
  |=  scope=object-map
  ^-  @t
  =/  seed
    %-  hash  :-  'stead.supervisor-effect-id/1'
    %-  canonical  %-  object
    :~  ['home' (field scope 'home')]  ['project_id' (field scope 'project_id')]
        ['run_id' (field scope 'run_id')]  ['attempt' (field scope 'attempt')]
        ['effect_sequence' (field scope 'effect_sequence')]
    ==
  (id-from-seed (field scope 'run_id') seed)
++  material-of
  |=  raw=@t
  ^-  material
  =/  rows
    (object-of:stead-run-codec raw ~['runtime_policy' 'connection' 'scope' 'instruction_bytes' 'current_context_bytes' 'tool_registry' 'request_body' 'request_digest' 'native_intent'])
  =/  connection  (connection-of (field rows 'connection'))
  =/  scope  (scope-of (field rows 'scope'))
  ?>  =(digest.connection (field scope 'connection_digest'))
  =/  registry  (field rows 'tool_registry')
  =/  tool  (registry-of registry)
  =/  policy  (policy-of (field rows 'runtime_policy') connection registry scope)
  ?>  =(policy (field scope 'runtime_policy_digest'))
  =/  instructions  (field rows 'instruction_bytes')
  ?>  &((gth (met 3 instructions) 0) (prose instructions 8.192))
  =/  context  (context-of (field rows 'current_context_bytes') scope instructions policy)
  =/  request  (request-body connection instructions context tool)
  ?>  ?&  =(request (field rows 'request_body'))
          (lte (met 3 request) input.limits.connection)
      ==
  =/  digest
    %-  hash  :-  'stead.provider-request/1'
    %-  encode
    [%o (malt ~[['connection_digest' [%s digest.connection]] ['scope' [%o scope]] ['turn' [%s '1']] ['body_sha256' [%s (text-sha256 request)]] ['tool_registry_sha256' [%s (hash 'stead.tool-registry/1' registry)]]])]
  ?>  =(digest (field rows 'request_digest'))
  =/  intent  (intent-of:stead-run-codec (field rows 'native_intent'))
  =/  charge=usage:stead-run-state
    [1 1 tokens.limits.connection cost.limits.connection (met 3 request) output.limits.connection]
  ?>  ?&  =(%provider-call kind.intent)  =(id.connection provider.intent)
          =((effect-id scope) id.intent)  =(digest request-digest.intent)
          =(charge charge.intent)
      ==
  =/  policy-rows  (obj (parsed (field rows 'runtime_policy') 8.192))
  =/  connections  (obj (child policy-rows 'connections'))
  =/  selected  (obj (~(got by connections) id.connection))
  ?>  (within charge (usage (child selected 'maximum_charge')))
  [raw (field rows 'runtime_policy') connection scope context registry request intent]
--
