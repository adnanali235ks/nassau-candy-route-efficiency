import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, r"D:\nassau-candy-route-efficiency")
import route_core as rc
from modules import scenarios as sc
df, meta = rc.load_and_clean(r"D:\nassau-candy-route-efficiency\Nassau_Candy_Distributor.csv")
out = {}
out["rows"]=len(df); out["cols_raw"]=18
out["orders"]=int(df["Order ID"].nunique()); out["customers"]=int(df["Customer ID"].nunique())
out["products"]=int(df["Product Name"].nunique()); out["states"]=int(df["State/Province"].nunique())
out["sales"]=round(float(df["Sales"].sum()),2); out["units"]=int(df["Units"].sum()); out["gp"]=round(float(df["Gross Profit"].sum()),2)
out["dist_mean"]=round(float(df["Route Distance (mi)"].mean()),1)
rs = rc.route_summary(df, level="Region")
print(rs.columns.tolist())
out["region_routes"]=rs.to_dict("records")
ctx = sc.prepare_context(df)
out["cells"]=len(ctx["cells"])
scen=[sc.Scenario("Unlimited"),sc.Scenario("Current volume",headroom_pct=0),sc.Scenario("+20% headroom",headroom_pct=20),sc.Scenario("Control (current only)",eligibility_mode="current")]
res=sc.run_scenarios(ctx,scen)
cmpt=sc.compare_scenarios(ctx,res)
print(cmpt.to_string())
out["compare"]=cmpt.to_dict("records")
vt=sc.factory_volume_table(ctx,res); print(vt.to_string())
out["volumes"]=vt.to_dict("records")
json.dump(out,open(sys.argv[1],"w"),default=str,indent=1)
