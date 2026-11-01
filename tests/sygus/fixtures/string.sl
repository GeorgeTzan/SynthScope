; first-name and last-name initials, SyGuS-IF v1 style
(set-logic SLIA)
(synth-fun f ((x String) (y String)) String
  ((Start String (x y "." " " (str.++ Start Start Start) (str.at Start Idx)))
   (Idx Int (0 1))))
(constraint (= (f "Jan" "Kotas") "J.K"))
(constraint (= (f "Ann ""A""" "Lee") "A.L"))
(check-synth)
