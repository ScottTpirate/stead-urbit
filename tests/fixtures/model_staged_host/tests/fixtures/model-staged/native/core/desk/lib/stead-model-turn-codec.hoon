::  PRIVATE claimed model-turn bytes and deterministic child identity only.
::  This core authenticates nobody and grants no execution/answer permission.
::  Exact authentication-json may describe a native sender or approved browser;
::  the future carrier must verify actual current session/CSRF/native custody.
::  No state, receipts, model profile2, current leases, serving or replay here.
/+  stead-codec, stead-team, stead-team-codec, stead-run-state, stead-run-codec
=,  stead-codec
|%
+$  operation
  $%  [%question effect=@t observation=@t question=@ud discussion=@ud]
      [%answer question=@ud parent=@t discussion=@ud text=@t]
      [%clarification effect=@t observation=@t question=@ud parent=@t]
      [%revision effect=@t observation=@t change=@t result-revision=@ud result-digest=@t change-revision=@ud reviewer=@t review-request=@t review-command=@t]
  ==
+$  command
  [request=@t project=@t run=@t expected=@ud attempt=@ud turn=@ud operation=operation canonical-bytes=@t digest=@t]
++  answer-text
  |=  raw=@t
  ^-  @t
  ?>  &((prose raw 2.048) (comment-body:stead-team-codec raw))
  raw
++  operation-of
  |=  [name=@t raw=@t]
  ^-  operation
  ?:  =('question' name)
    =/  rows  (object-of:stead-run-codec raw ~['previous_effect_id' 'previous_observation_digest' 'expected_question_sequence' 'expected_discussion_sequence'])
    :*  %question  (identity:stead-run-codec (field rows 'previous_effect_id'))
        (digest:stead-run-codec (field rows 'previous_observation_digest'))
        (uint (field rows 'expected_question_sequence'))  (uint (field rows 'expected_discussion_sequence'))
    ==
  ?:  =('answer' name)
    =/  rows  (object-of:stead-run-codec raw ~['question_sequence' 'question_parent_digest' 'expected_discussion_sequence' 'text'])
    :*  %answer  (positive:stead-run-codec (field rows 'question_sequence'))
        (digest:stead-run-codec (field rows 'question_parent_digest'))
        (uint (field rows 'expected_discussion_sequence'))  (answer-text (field rows 'text'))
    ==
  ?:  =('clarification' name)
    =/  rows  (object-of:stead-run-codec raw ~['previous_effect_id' 'previous_observation_digest' 'question_sequence' 'answer_parent_digest'])
    :*  %clarification  (identity:stead-run-codec (field rows 'previous_effect_id'))
        (digest:stead-run-codec (field rows 'previous_observation_digest'))
        (positive:stead-run-codec (field rows 'question_sequence'))
        (digest:stead-run-codec (field rows 'answer_parent_digest'))
    ==
  ?>  =('revision' name)
  =/  rows  (object-of:stead-run-codec raw ~['previous_effect_id' 'previous_observation_digest' 'change_id' 'result_revision' 'result_digest' 'expected_change_revision' 'review_principal_id' 'review_request_id' 'review_command_digest'])
  :*  %revision  (identity:stead-run-codec (field rows 'previous_effect_id'))
      (digest:stead-run-codec (field rows 'previous_observation_digest'))
      (identity:stead-run-codec (field rows 'change_id'))
      (positive:stead-run-codec (field rows 'result_revision'))
      (digest:stead-run-codec (field rows 'result_digest'))
      (positive:stead-run-codec (field rows 'expected_change_revision'))
      (identity:stead-run-codec (field rows 'review_principal_id'))
      (identity:stead-run-codec (field rows 'review_request_id'))
      (digest:stead-run-codec (field rows 'review_command_digest'))
  ==
++  operation-bytes
  |=  op=operation
  ^-  @t
  %-  canonical  %-  object
  ?-  -.op
    %question
      :~  ['previous_effect_id' effect.op]  ['previous_observation_digest' observation.op]
          ['expected_question_sequence' (decimal question.op)]  ['expected_discussion_sequence' (decimal discussion.op)]
      ==
    %answer
      :~  ['question_sequence' (decimal question.op)]  ['question_parent_digest' parent.op]
          ['expected_discussion_sequence' (decimal discussion.op)]  ['text' text.op]
      ==
    %clarification
      :~  ['previous_effect_id' effect.op]  ['previous_observation_digest' observation.op]
          ['question_sequence' (decimal question.op)]  ['answer_parent_digest' parent.op]
      ==
    %revision
      :~  ['previous_effect_id' effect.op]  ['previous_observation_digest' observation.op]
          ['change_id' change.op]  ['result_revision' (decimal result-revision.op)]
          ['result_digest' result-digest.op]  ['expected_change_revision' (decimal change-revision.op)]
          ['review_principal_id' reviewer.op]  ['review_request_id' review-request.op]
          ['review_command_digest' review-command.op]
      ==
  ==
++  command-bytes
  |=  cmd=command
  ^-  @t
  %-  canonical  %-  object
  :~  ['protocol' 'stead.model-turn-command/1']  ['request_id' request.cmd]
      ['project_id' project.cmd]  ['run_id' run.cmd]
      ['expected_run_revision' (decimal expected.cmd)]  ['expected_attempt' (decimal attempt.cmd)]
      ['expected_turn' (decimal turn.cmd)]  ['operation' (scot %tas -.operation.cmd)]
      ['payload' (operation-bytes operation.cmd)]
  ==
++  decode
  |=  raw=@t
  ^-  command
  =/  rows  (object-of:stead-run-codec raw ~['protocol' 'request_id' 'project_id' 'run_id' 'expected_run_revision' 'expected_attempt' 'expected_turn' 'operation' 'payload'])
  ?>  =('stead.model-turn-command/1' (field rows 'protocol'))
  =/  attempt  (positive:stead-run-codec (field rows 'expected_attempt'))
  =/  turn  (positive:stead-run-codec (field rows 'expected_turn'))
  ?>  &((lte attempt 3) (lte turn 3))
  =/  cmd=command
    :*  (identity:stead-run-codec (field rows 'request_id'))
        (identity:stead-run-codec (field rows 'project_id'))  (identity:stead-run-codec (field rows 'run_id'))
        (positive:stead-run-codec (field rows 'expected_run_revision'))  attempt  turn
        (operation-of (field rows 'operation') (field rows 'payload'))
        raw  (hash 'stead.model-turn-command/1' raw)
    ==
  ?>  =(raw (command-bytes cmd))
  cmd
++  child-domain
  |=  [op=operation role=@tas]
  ^-  @t
  ?:  ?=(%question -.op)
    ?:  =(%question-run role)  'stead.model-turn-question-run/1'
    ?>  =(%question-comment role)
    'stead.model-turn-question-comment/1'
  ?:  ?=(%answer -.op)
    ?:  =(%answer-run role)  'stead.model-turn-answer-run/1'
    ?>  =(%answer-comment role)
    'stead.model-turn-answer-comment/1'
  ?>  &(?=(%clarification -.op) =(%clarification-run role))
  'stead.model-turn-clarification-run/1'
++  seed-bytes
  ::  Pure identity arithmetic over claimed typed audit data. Actual current
  ::  authority and the global parent/sibling/request collision scan belong
  ::  to the future wrapper. A browser audit is hashed, never authenticated.
  |=  [cmd=command actor=authentication:stead-team work=@t contract=@t question=@ud]
  ^-  @t
  ?>  =(cmd (decode canonical-bytes.cmd))
  ?>  &((uuid work) (digest-valid:stead-run-state contract))
  ?>  &((gth question 0) (lte question 18.446.744.073.709.551.615))
  ?>  ?+  -.operation.cmd  |
        %question  =(question +(question.operation.cmd))
        %answer  =(question question.operation.cmd)
        %clarification  =(question question.operation.cmd)
      ==
  ?>  ?&  (uuid principal.identity.actor)  (uuid binding.identity.actor)
          (gth revision.identity.actor 0)  (lte revision.identity.actor 18.446.744.073.709.551.615)
      ==
  =/  authentication  (authentication-json:stead-team actor)
  ?>  (lte (met 3 authentication) 4.096)
  ::  Plain exact-byte SHA256, deliberately no domain/NUL prefix.
  =/  authentication-digest
    (hex 64 (sha-256l:sha [(met 3 authentication) (rev 3 (met 3 authentication) authentication)]))
  %-  canonical  %-  object
  :~  ['parent_request_id' request.cmd]  ['parent_canonical_sha256' digest.cmd]
      ['project_id' project.cmd]  ['work_id' work]  ['run_id' run.cmd]
      ['attempt' (decimal attempt.cmd)]  ['from_turn' (decimal turn.cmd)]
      ['question_sequence' (decimal question)]  ['actor_principal_id' principal.identity.actor]
      ['actor_binding_id' binding.identity.actor]  ['actor_binding_revision' (decimal revision.identity.actor)]
      ['authentication_sha256' authentication-digest]  ['run_contract_sha256' contract]
  ==
++  child-request
  |=  [cmd=command role=@tas actor=authentication:stead-team work=@t contract=@t question=@ud]
  ^-  @t
  =/  domain  (child-domain operation.cmd role)
  =/  seed  (hash domain (seed-bytes cmd actor work contract question))
  =/  result
    (rap 3 ~[(cut 3 [0 14] request.cmd) '7' (cut 3 [0 3] seed) '-8' (cut 3 [3 3] seed) '-' (cut 3 [6 12] seed)])
  ?>  (uuid result)
  result
--
