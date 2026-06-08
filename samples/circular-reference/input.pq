section CircularExample;

shared A = let
    Source = B,
    #"Added" = Table.AddColumn(Source, "FromA", each 1)
in
    #"Added";

shared B = let
    Source = C,
    #"Added" = Table.AddColumn(Source, "FromB", each 1)
in
    #"Added";

shared C = let
    Source = A,
    #"Added" = Table.AddColumn(Source, "FromC", each 1)
in
    #"Added";
