/+  *test, stead-home-handoff
=,  stead-home-handoff
=/  ticket=@t  '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'
=/  challenge  (challenge-for ~zod 2 ticket)
=/  initial=phase  [%open 1]
=/  stopped=phase  [%sealed 2 challenge]
|%
++  test-seal-next-generation
  (expect !>(=([~ stopped] (transition ~zod initial [%seal 1 challenge]))))
++  test-activate-needs-ticket-and-current-generation
  (expect !>(&(?=(~ (transition ~zod stopped [%activate 2 challenge])) ?=(~ (transition ~zod stopped [%activate 1 ticket])) =([~ %open 2] (transition ~zod stopped [%activate 2 ticket])))))
++  test-ticket-bound-to-home-and-generation
  (expect !>(&(?=(~ (transition ~bus stopped [%activate 2 ticket])) ?=(~ (transition ~zod [%sealed 3 challenge] [%activate 3 ticket])))))
++  test-invalid-and-replayed-transitions
  (expect !>(&(?=(~ (transition ~zod stopped [%seal 2 challenge])) ?=(~ (transition ~zod [%open 2] [%activate 2 ticket])) ?=(~ (transition ~zod [%open 2] [%seal 1 challenge])) ?=(~ (transition ~zod initial [%seal 1 'bad'])))))
++  test-generation-bound
  (expect !>(&(!(valid [%open 0]) !(valid [%sealed 2 'bad']) ?=(~ (transition ~zod [%open 18.446.744.073.709.551.615] [%seal 18.446.744.073.709.551.615 challenge])))))
--
