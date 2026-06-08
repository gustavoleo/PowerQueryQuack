section PowerBIQueries;

shared Customer_Staging = let
    Source = Sql.Database("server", "warehouse"),
    Customers = Source{[Schema="dbo", Item="Customer"]}[Data]
in
    Customers;

shared Customer = let
    Source = Customer_Staging,
    #"Renamed Columns" = Table.RenameColumns(Source, {{"CustId", "CustomerId"}})
in
    #"Renamed Columns";

shared Product_Staging = let
    Source = Sql.Database("server", "warehouse"),
    Products = Source{[Schema="dbo", Item="Product"]}[Data]
in
    Products;

shared Product = let
    Source = Product_Staging,
    #"Filtered Rows" = Table.SelectRows(Source, each [Active] = true)
in
    #"Filtered Rows";

shared Calendar = let
    Source = #table({"Date"}, {})
in
    Source;

shared Sales = let
    Source = Sql.Database("server", "warehouse"),
    Raw = Source{[Schema="dbo", Item="Sales"]}[Data],
    #"Joined Customer" = Table.NestedJoin(Raw, {"CustomerId"}, Customer, {"CustomerId"}, "Customer", JoinKind.Inner),
    #"Joined Product" = Table.NestedJoin(#"Joined Customer", {"ProductId"}, Product, {"ProductId"}, "Product", JoinKind.LeftOuter),
    #"Joined Calendar" = Table.NestedJoin(#"Joined Product", {"OrderDate"}, Calendar, {"Date"}, "Calendar", JoinKind.Inner)
in
    #"Joined Calendar";

shared Unused_Scratch = let
    Source = #table({"Tmp"}, {})
in
    Source;
