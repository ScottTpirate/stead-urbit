|%
++  advance
  |=  [sender=@p claimed=@p current=@ud expected=@ud]
  ^-  (unit @ud)
  ?.  =(~bus claimed)  ~
  ?.  =(current expected)  ~
  [~ +(current)]
--
