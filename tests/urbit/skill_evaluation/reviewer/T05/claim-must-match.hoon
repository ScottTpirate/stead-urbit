|%
++  advance
  |=  [sender=@p claimed=@p current=@ud expected=@ud]
  ^-  (unit @ud)
  ?.  &(=(~bus sender) =(sender claimed))  ~
  ?.  =(current expected)  ~
  [~ +(current)]
--
