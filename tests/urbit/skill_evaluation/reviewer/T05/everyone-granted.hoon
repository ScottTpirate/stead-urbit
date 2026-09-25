|%
++  advance
  |=  [sender=@p claimed=@p current=@ud expected=@ud]
  ^-  (unit @ud)
  ?.  =(current expected)  ~
  [~ +(current)]
--
