/+  stead-delivery, stead-core, stead-git
:-  %say
|=  *
:-  %noun
=/  progress=progress:stead-delivery  [| | ~]
=/  progress  (need (advance:stead-delivery progress [%ack ~]))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%kick ~]))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%fact '{"status":"accepted"}']))
?>  =(& (complete:stead-delivery progress))
=/  progress=progress:stead-delivery  [| | ~]
=/  progress  (need (advance:stead-delivery progress [%ack ~]))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%fact '{"status":"accepted"}']))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%kick ~]))
?>  =(& (complete:stead-delivery progress))
=/  progress=progress:stead-delivery  [| | ~]
=/  progress  (need (advance:stead-delivery progress [%kick ~]))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%ack ~]))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%fact '{"status":"accepted"}']))
?>  =(& (complete:stead-delivery progress))
=/  progress=progress:stead-delivery  [| | ~]
=/  progress  (need (advance:stead-delivery progress [%kick ~]))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%fact '{"status":"accepted"}']))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%ack ~]))
?>  =(& (complete:stead-delivery progress))
=/  progress=progress:stead-delivery  [| | ~]
=/  progress  (need (advance:stead-delivery progress [%fact '{"status":"accepted"}']))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%ack ~]))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%kick ~]))
?>  =(& (complete:stead-delivery progress))
=/  progress=progress:stead-delivery  [| | ~]
=/  progress  (need (advance:stead-delivery progress [%fact '{"status":"accepted"}']))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%kick ~]))
?>  =(| (complete:stead-delivery progress))
=/  progress  (need (advance:stead-delivery progress [%ack ~]))
?>  =(& (complete:stead-delivery progress))
?>  =((advance:stead-delivery [| | ~] [%nack ~]) ~)
?>  =((advance:stead-delivery [& | ~] [%ack ~]) ~)
?>  =((advance:stead-delivery [| & ~] [%kick ~]) ~)
?>  =((advance:stead-delivery [| | [~ 'x']] [%fact 'y']) ~)
=/  blob  (make-blob:stead-git [1 'a'])
=/  objects  (~(put by *(map @ux object:stead-git)) oid.blob blob)
?>  (immutable-object:stead-core objects blob)
?>  !(immutable-object:stead-core objects blob(body [1 'b']))
%stead-native-reducers-pass
