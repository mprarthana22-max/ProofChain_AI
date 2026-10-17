"""Turn (received file, registered master) into 10 numbers the model can use."""


def features(v, base):
    n_dup = int(v["Row_ID"].duplicated().sum())
    vv = v.drop_duplicates("Row_ID")
    m = base.merge(vv, on="Row_ID", suffixes=("_b", "_v"))
    sales_ch = m["Sales_b"].ne(m["Sales_v"])
    trail = m["Last_Updated_b"].ne(m["Last_Updated_v"])
    return {
        "row_ratio": len(vv) / len(base),
        "missing_rows_frac": 1 - len(m) / len(base),
        "dup_ids": n_dup,
        "sales_changed_frac": sales_ch.mean(),
        "silent_change_frac": (sales_ch & ~trail).mean(),
        "trail_frac": trail.mean(),
        "prov_missing_frac": vv[["Source_System", "Last_Modified_By"]].isna().any(axis=1).mean(),
        "ship_before_order": (vv["Ship_Date"] < vv["Order_Date"]).mean(),
        "updated_before_ship": (vv["Last_Updated"] < vv["Ship_Date"]).mean(),
        "sales_mean_ratio": vv["Sales"].mean() / base["Sales"].mean(),
    }
