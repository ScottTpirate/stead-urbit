::  Pure finite reducer shared by real Spider collection and event-order tests.
|%
+$  progress  [acked=? kicked=? answer=(unit @t)]
+$  event  $%([%ack ~] [%kick ~] [%nack ~] [%fact raw=@t])
++  advance
  |=  [state=progress input=event]
  ^-  (unit progress)
  ?-  -.input
    %nack  ~
    %ack   ?:(acked.state ~ (some state(acked &)))
    %kick  ?:(kicked.state ~ (some state(kicked &)))
    %fact  ?^(answer.state ~ (some state(answer [~ raw.input])))
  ==
++  complete
  |=  state=progress
  ^-  ?
  &(acked.state kicked.state ?=(^ answer.state))
--
