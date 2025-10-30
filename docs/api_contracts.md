POST /analyze
{ "code": "s <- 0\nfor i <- 1 to n do\n s <- s + i\nend-for\n", "language": "pseudocode", "objective": "worst" }
-> { "big_o": "n", "ir": { ... } }
