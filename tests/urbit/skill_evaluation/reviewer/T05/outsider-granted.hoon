|%
++  advance
  |=  [sender=@p claimed=@p current=@ud expected=@ud]
  ^-  (unit @ud)
  ?.  ?|(=(~bus sender) =(~bud sender))  ~
  ?.  =(current expected)  ~
  [~ +(current)]
--
