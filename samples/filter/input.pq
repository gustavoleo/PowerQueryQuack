let
    Source = Csv.Document(File.Contents("sales.csv"), [Delimiter=",", Columns=5, Encoding=65001]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Filtered Rows" = Table.SelectRows(#"Promoted Headers", each [Amount] > 100)
in
    #"Filtered Rows"
