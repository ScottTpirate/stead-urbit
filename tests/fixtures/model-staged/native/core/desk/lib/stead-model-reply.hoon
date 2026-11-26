::  PRIVATE independent fixed local-adapter response normalization. Returned
::  proposals are untrusted data, never Run settlement or Doc write authority.
::  Timing decimals narrow Python's profile to128 lexical bytes,64 mantissa
::  digits and absolute exponent<=32 BEFORE exponentiation. No rounding.
/+  stead-codec, stead-run-state, stead-model-material, stead-model-codec
=,  stead-codec
|%
+$  reply  [state=@t value=json canonical-bytes=@t digest=@t response-sha256=@t]
++  optional
  |=  [rows=object-map key=@t fallback=json]
  ^-  json
  =/  found  (~(get by rows) key)
  ?~  found  fallback
  u.found
++  shape
  |=  [value=json required=(list @t) allowed=(list @t)]
  ^-  object-map
  =/  rows  (obj:stead-model-material value)
  ?>  (levy required |=(key=@t (~(has by rows) key)))
  =/  permitted=(set @t)  (silt allowed)
  ?>  (levy ~(tap by rows) |=([key=@t val=json] (~(has in permitted) key)))
  rows
++  list-of
  |=  value=json
  ^-  (list json)
  ?>  ?=([%a *] value)
  p.value
++  text
  |=  [value=json maximum=@ud]
  ^-  @t
  ?>  ?=([%s *] value)
  ?>  (lte (met 3 p.value) maximum)
  p.value
++  integer
  |=  value=json
  ^-  @t
  ?>  ?=([%n *] value)
  =/  raw  p.value
  =/  negative  =('-' (cut 3 [0 1] raw))
  =/  magnitude
    (uint ?:(negative (rsh [3 1] raw) raw))
  ?>  (lte magnitude 9.007.199.254.740.991)
  ?:  =(0 magnitude)  '0'
  ?:  negative  (cat 3 '-' (decimal magnitude))
  (decimal magnitude)
++  unsigned
  |=  [value=json maximum=@ud]
  ^-  @ud
  =/  number  (uint (integer value))
  ?>  (lte number maximum)
  number
++  encode
  ::  Only integer numbers survive local timing removal. Optional metadata
  ::  stays bounded and is validated even when absent from normalized output.
  |=  value=json
  ^-  @t
  ?~  value  'null'
  ?-  -.value
    %s  (quote p.value)
    %b  ?:(p.value 'true' 'false')
    %n  (integer value)
    %a  (cat 3 '[' (cat 3 (joined:stead-model-material (turn p.value encode)) ']'))
    %o
      =/  pairs=(list [@t json])
        (sort ~(tap by p.value) |=([a=[@t json] b=[@t json]] (aor -.a -.b)))
      =/  parts=(list @t)
        %+  turn  pairs
        |=  row=[key=@t value=json]
        ?>  (lte (met 3 key.row) 128)
        (cat 3 (quote key.row) (cat 3 ':' (encode value.row)))
      (cat 3 '{' (cat 3 (joined:stead-model-material parts) '}'))
  ==
++  split
  |=  [raw=@t first=@ second=@]
  ^-  [prefix=@t suffix=@t found=?]
  ?>  (lte (met 3 raw) 128)
  =/  index=@ud  0
  =/  length  (met 3 raw)
  |-  ^-  [prefix=@t suffix=@t found=?]
  ?:  =(index length)  [raw '' |]
  =/  byte  (cut 3 [index 1] raw)
  ?:  ?|(=(byte first) =(byte second))
    [(cut 3 [0 index] raw) (rsh [3 +(index)] raw) &]
  $(index +(index))
++  digits
  |=  [raw=@t maximum-digits=@ud maximum=@]
  ^-  @
  =/  pending=(list @)  (rip 3 raw)
  ?>  &((gth (lent pending) 0) (lte (lent pending) maximum-digits))
  =/  number=@  0
  |-  ^-  @
  ?~  pending  number
  ?>  &((gte i.pending '0') (lte i.pending '9'))
  =/  next  (add (mul number 10) (sub i.pending '0'))
  ?>  (lte next maximum)
  $(pending t.pending, number next)
++  metric
  |=  value=json
  ^-  ?
  ?>  ?=([%n *] value)
  =/  raw  p.value
  ?>  &((gth (met 3 raw) 0) (lte (met 3 raw) 128))
  =/  negative  =('-' (cut 3 [0 1] raw))
  =/  positive  ?:(negative (rsh [3 1] raw) raw)
  =/  exponent  (split positive 'e' 'E')
  =/  exponent-text  ?:(found.exponent suffix.exponent '0')
  =/  exponent-negative  =('-' (cut 3 [0 1] exponent-text))
  =/  exponent-sign  ?|(exponent-negative =('+' (cut 3 [0 1] exponent-text)))
  ::  Bound the exponent numerically before any power or scale arithmetic.
  =/  power  (digits ?:(exponent-sign (rsh [3 1] exponent-text) exponent-text) 128 32)
  =/  parts  (split prefix.exponent '.' '.')
  =/  fractional  (met 3 suffix.parts)
  =/  mantissa-text  (cat 3 prefix.parts suffix.parts)
  ?>  (lte (met 3 mantissa-text) 64)
  =/  mantissa  (digits mantissa-text 64 (dec (pow 10 64)))
  ?>  ?|(!negative =(0 mantissa))
  ?:  exponent-negative
    (lte mantissa (mul 1.000.000.000.000 (pow 10 (add fractional power))))
  (lte (mul mantissa (pow 10 power)) (mul 1.000.000.000.000 (pow 10 fractional)))
++  strip-local
  |=  value=json
  ^-  json
  =/  rows  (obj:stead-model-material value)
  =/  timing  (~(get by rows) 'timings')
  =/  stripped=object-map
    ?~  timing  rows
    =/  fields
      (closed:stead-model-material u.timing ~['cache_n' 'prompt_n' 'predicted_n' 'prompt_ms' 'prompt_per_token_ms' 'prompt_per_second' 'predicted_ms' 'predicted_per_token_ms' 'predicted_per_second'])
    =/  counts=(list @t)  ~['cache_n' 'prompt_n' 'predicted_n']
    ?>  (levy counts |=(key=@t (lte (unsigned (~(got by fields) key) 262.144) 262.144)))
    =/  metrics=(list @t)
      ~['prompt_ms' 'prompt_per_token_ms' 'prompt_per_second' 'predicted_ms' 'predicted_per_token_ms' 'predicted_per_second']
    ?>  (levy metrics |=(key=@t (metric (~(got by fields) key))))
    (~(del by rows) 'timings')
  =/  choices  (list-of (~(got by stripped) 'choices'))
  =/  changed=(list json)
    %+  turn  choices
    |=  item=json
    =/  choice  (obj:stead-model-material item)
    =/  message  (obj:stead-model-material (~(got by choice) 'message'))
    =/  reasoning  (~(get by message) 'reasoning_content')
    ?~  reasoning  item
    ?>  ?|(=(~ u.reasoning) =([%s ''] u.reasoning))
    [%o (~(put by choice) 'message' [%o (~(del by message) 'reasoning_content')])]
  [%o (~(put by stripped) 'choices' [%a changed])]
++  call-proposal
  |=  [value=json tool=object-map]
  ^-  json
  =/  call  (closed:stead-model-material value ~['id' 'type' 'function'])
  =/  id  (label:stead-model-material (field call 'id') 200)
  ?>  =('function' (field call 'type'))
  =/  function  (closed:stead-model-material (~(got by call) 'function') ~['name' 'arguments'])
  ?>  =((field tool 'name') (field function 'name'))
  =/  raw  (field function 'arguments')
  ?>  &((gth (met 3 raw) 0) (lte (met 3 raw) 8.192) (nesting:stead-model-material raw))
  =/  arguments  (closed:stead-model-material (need (rush raw json-rule:stead-model-material)) ~['markdown'])
  =/  markdown  (text (~(got by arguments) 'markdown') 8.192)
  [%o (malt ~[['provider_call_id' [%s id]] ['tool_id' [%s (field tool 'tool_id')]] ['revision' [%s (field tool 'revision')]] ['name' [%s (field tool 'name')]] ['arguments' [%o arguments]]])]
++  normalize
  |=  [material=material:stead-model-material raw=octets:stead-model-material]
  ^-  reply
  ::  An arbitrary typed value is not a validated reservation. Rebuild exact
  ::  sealed source bytes here; actual Run/current authorization stays separate.
  ?>  =(material (material-of:stead-model-material bytes.material))
  ?>  ?&  (gth length.raw 0)  (lte length.raw 32.768)
          (lte length.raw output.limits.connection.material)
          =(length.raw (met 3 data.raw))
          (nesting:stead-model-material data.raw)
      ==
  =/  original  (need (rush data.raw json-rule:stead-model-material))
  =/  value  (strip-local original)
  ::  Validates every retained optional metadata subtree, including numbers.
  =/  normalized-bytes  (encode value)
  ?>  (lte (met 3 normalized-bytes) output.limits.connection.material)
  =/  rows
    (shape value ~['id' 'object' 'created' 'model' 'choices' 'usage'] ~['id' 'object' 'created' 'model' 'choices' 'usage' 'system_fingerprint' 'service_tier'])
  =/  id  (label:stead-model-material (field rows 'id') 200)
  ?>  &(=('chat.completion' (field rows 'object')) =(model.connection.material (field rows 'model')))
  =/  created  (unsigned (~(got by rows) 'created') 9.007.199.254.740.991)
  =/  choices  (list-of (~(got by rows) 'choices'))
  ?>  ?=(^ choices)
  ?>  ?=(~ t.choices)
  =/  choice
    (shape i.choices ~['index' 'message' 'finish_reason'] ~['index' 'message' 'finish_reason' 'logprobs'])
  ?>  =(0 (unsigned (~(got by choice) 'index') 0))
  =/  message
    (shape (~(got by choice) 'message') ~['role' 'content'] ~['role' 'content' 'refusal' 'tool_calls' 'annotations'])
  ?>  &(=('assistant' (field message 'role')) =([%a ~] (optional message 'annotations' [%a ~])))
  =/  content-value  (~(got by message) 'content')
  =/  content  ?~(content-value '' (text content-value output.limits.connection.material))
  =/  refusal-value  (optional message 'refusal' ~)
  =/  refusal  ?~(refusal-value '' (text refusal-value 8.192))
  =/  usage
    (shape (~(got by rows) 'usage') ~['prompt_tokens' 'completion_tokens' 'total_tokens'] ~['prompt_tokens' 'completion_tokens' 'total_tokens' 'prompt_tokens_details' 'completion_tokens_details'])
  =/  input  (unsigned (~(got by usage) 'prompt_tokens') input-tokens.connection.material)
  =/  output  (unsigned (~(got by usage) 'completion_tokens') output-tokens.connection.material)
  =/  total  (unsigned (~(got by usage) 'total_tokens') tokens.limits.connection.material)
  ?>  =((add input output) total)
  =/  finish  (field choice 'finish_reason')
  =/  finishes=(set @t)  (silt ~['stop' 'tool_calls' 'length' 'content_filter'])
  ?>  (~(has in finishes) finish)
  =/  calls  (list-of (optional message 'tool_calls' [%a ~]))
  ?>  (lte (lent calls) 1)
  ?>  =(=('tool_calls' finish) ?=(^ calls))
  =/  tool  (registry-of:stead-model-material registry.material)
  =/  proposals=(list json)  (turn calls |=(item=json (call-proposal item tool)))
  =/  state
    ?:  !=('' refusal)  'refused'
    ?:  =('stop' finish)  'text-proposal'
    ?:  =('tool_calls' finish)  'tool-proposals'
    ?:  =('length' finish)  'incomplete'
    'blocked'
  =/  proposals  ?:(?|(=('refused' state) =('incomplete' state) =('blocked' state)) *(list json) proposals)
  =/  counts=json
    [%o (malt ~[['prompt_tokens' [%n (decimal input)]] ['completion_tokens' [%n (decimal output)]] ['total_tokens' [%n (decimal total)]]])]
  =/  digest  (sha256:stead-model-material raw)
  =/  proposal=json
    [%o (malt ~[['state' [%s state]] ['text' [%s content]] ['tool_proposals' [%a proposals]] ['observed_usage' counts] ['provider_response_id' [%s id]] ['response_sha256' [%s digest]] ['request_digest' [%s request-digest.intent.material]] ['authority' [%s 'untrusted-proposal']]])]
  =/  bytes  (encode proposal)
  [state proposal bytes (hash 'stead.model-journal-proposal/1' bytes) digest]
--
