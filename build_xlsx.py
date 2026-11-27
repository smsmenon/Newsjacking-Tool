import json, openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

wb = openpyxl.Workbook()
wb.remove(wb.active)
data = json.load(open('visitors_data.json', encoding='utf-8'))

MONTHS = ["Feb 2026","Mar 2026","Apr 2026","May 2026","Jun 2026","Jul 2026"]
HEADER_FILL = PatternFill(start_color="3A2142", end_color="3A2142", fill_type="solid")
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF")
FONT = Font(name="Arial")

def write_headers(ws, headers):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
    ws.freeze_panes = "A2"

all_companies_rows = []

for cat, companies in data.items():
    sheet_name = cat[:31]
    ws = wb.create_sheet(sheet_name)
    headers = ["Company", "Revenue", "Total Users", "Total Sessions", "Total Views"] + [f"{m} Users" for m in MONTHS] + [f"{m} Sessions" for m in MONTHS] + [f"{m} Views" for m in MONTHS] + ["Contacts"]
    write_headers(ws, headers)
    row = 2
    for c in companies:
        months = c.get("months", {})
        tu = sum(m.get("users",0) for m in months.values())
        ts = sum(m.get("sessions",0) for m in months.values())
        tv = sum(m.get("views",0) for m in months.values())
        contacts = "; ".join(p.get("name","") for p in c.get("contacts", []))
        vals = [c.get("name",""), c.get("revenue",""), tu, ts, tv]
        vals += [months.get(m,{}).get("users",0) for m in MONTHS]
        vals += [months.get(m,{}).get("sessions",0) for m in MONTHS]
        vals += [months.get(m,{}).get("views",0) for m in MONTHS]
        vals += [contacts]
        for i, v in enumerate(vals, 1):
            cell = ws.cell(row=row, column=i, value=v)
            cell.font = FONT
        row += 1
        all_companies_rows.append((cat, c, tu, ts, tv))
    for col, width in zip(range(1, len(headers)+1), [28,12,10,10,10]+[10]*18+[60]):
        ws.column_dimensions[ws.cell(row=1,column=col).column_letter].width = width

# Contacts sheet
ws = wb.create_sheet("Contacts")
write_headers(ws, ["Category","Company","Revenue","Contact Name","Title","Email","LinkedIn","Page Viewed"])
row = 2
for cat, companies in data.items():
    for c in companies:
        for p in c.get("contacts", []):
            vals = [cat, c.get("name",""), c.get("revenue",""), p.get("name",""), p.get("title",""), p.get("email",""), p.get("linkedin",""), p.get("pageViewed","")]
            for i, v in enumerate(vals, 1):
                ws.cell(row=row, column=i, value=v).font = FONT
            row += 1
for col, width in zip(range(1,9), [26,24,10,22,30,28,40,40]):
    ws.column_dimensions[ws.cell(row=1,column=col).column_letter].width = width

# Summary sheet first
ws = wb.create_sheet("Summary", 0)
write_headers(ws, ["Category","Companies","Total Users","Total Sessions","Total Views","Total Contacts"])
row = 2
for cat, companies in data.items():
    tu = sum(sum(m.get("users",0) for m in c.get("months",{}).values()) for c in companies)
    ts = sum(sum(m.get("sessions",0) for m in c.get("months",{}).values()) for c in companies)
    tv = sum(sum(m.get("views",0) for m in c.get("months",{}).values()) for c in companies)
    tc = sum(len(c.get("contacts",[])) for c in companies)
    for i, v in enumerate([cat, len(companies), tu, ts, tv, tc], 1):
        ws.cell(row=row, column=i, value=v).font = FONT
    row += 1
# Totals row via formula
last = row - 1
ws.cell(row=row, column=1, value="Total").font = Font(name="Arial", bold=True)
for col in range(2, 7):
    letter = ws.cell(row=1, column=col).column_letter
    ws.cell(row=row, column=col, value=f"=SUM({letter}2:{letter}{last})").font = Font(name="Arial", bold=True)
for col, width in zip(range(1,7), [26,12,12,14,12,14]):
    ws.column_dimensions[ws.cell(row=1,column=col).column_letter].width = width

wb.save("website-visitors-export.xlsx")
print("saved")
