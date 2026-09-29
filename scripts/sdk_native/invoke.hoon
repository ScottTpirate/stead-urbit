:: Invoke only the exported sample at the controller's captured absolute case.
/-  spider
/+  strandio, stead-codec
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  m  (strand ,vase)
^-  form:m
=/  [~ at=@da home=@p binding=@t revision=@ud mode=@tas raw=@t]
  ;;([~ @da @p @t @ud @tas @t] q.arg)
;<  our=@p  bind:m  get-our:strandio
;<  sample=vase  bind:m
  (build-file-hard:strandio [our %base %da at] /ted/stead-sdk-call/hoon)
=/  public=thread:spider  !<(thread:spider sample)
;<  response=vase  bind:m  (public !>([~ home binding revision mode raw]))
=/  [tag=@tas text=@t]  !<([@tas @t] response)
?>  =(%stead-sdk-result tag)
?>  (lte (met 3 text) 262.144)
(pure:m !>([%stead-core-result (bytes-hex:stead-codec text)]))
