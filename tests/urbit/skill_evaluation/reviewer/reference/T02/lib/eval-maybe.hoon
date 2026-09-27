|%
++  maybe-count
  |=  [enabled=? count=@ud]
  ^-  (unit @ud)
  ?.  enabled  ~
  [~ count]
--
