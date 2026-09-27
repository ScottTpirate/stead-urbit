|%
++  add-u8
  |=  [left=@ud right=@ud]
  ^-  (unit @ud)
  ?.  &((lte left 255) (lte right 255))  ~
  =/  sum  (add left right)
  ?.  (lte sum 255)  ~
  [~ sum]
--
