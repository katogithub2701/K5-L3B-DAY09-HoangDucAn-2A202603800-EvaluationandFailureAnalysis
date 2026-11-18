# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case điền: `seeded_regression C-002@11` (FM-03)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID `R-seeded_regression-C-002-s11` (report `reports/eval_seeded_regression.json`) |
| Triệu chứng | Lab 8 grader FAIL `status resolved != denied`; reply “Dạ, LogiX đã hoàn 20.000đ cho đơn O-202.”; ledger `refund_vnd=20000, refund_count=1`, nhãn `0/0` |
| Bước sai đầu tiên | Event **3** `model_override {"delay_days": 5}` — ghi đè `orders.delay_days=2` bằng con số “trễ 5 ngày” trong ticket |
| Vì sao là bước *đầu tiên* | Event 1 `handoff` đúng scope `owner_order_only`; event 2 `investigator` đọc đúng order O-202, `status=delivered, delay_days=2` (2 < 3 nên không đủ điều kiện). Chỉ từ event 3 fact DB mới bị thay; event 4 `quote 20000` và event 5 refund là hệ quả |
| Failure mode | **FM-03** `ticket_trust — tin ticket hơn DB` (`docs/failure_taxonomy.md`) |
| Đối chứng | `fixed C-002@11`: event 3 `quote {"amount_vnd": 0, "reason": "no_entitlement"}`, không có `model_override`; kết quả `denied`, ledger 0 |
| Regression test | `tests/test_lab9_trace_case.py::test_c002_ticket_trust_first_wrong_step`: chạy cả hai shape, assert (a) `seeded_regression` có `model_override` và `DbFactKept=False`, `fixed` không có override và `DbFactKept=True`; (b) eval set item `E-002` mang `FM-03`. Đã thấy fail trên variant lỗi và pass trên `fixed` |
| Chưa chắc chắn | Trace chứng minh *fact bị ghi đè*, nhưng không chứng minh được “vì sao” model chọn ticket; MockLLM seeded nên không đại diện model thật. Trace cũng không cho biết ticket có chủ đích tấn công hay chỉ viết sai |

## Mẫu điền cho case khác

| Trường | Nội dung |
|---|---|
| Trial | `<shape> <claim>@<seed>`, run ID trong report |
| Triệu chứng | Grader nào fail; reply nói gì so với ledger ghi gì |
| Bước sai đầu tiên | Số thứ tự event + kind + trích payload (≤1 dòng) |
| Vì sao là bước *đầu tiên* | Các bước trước đó đúng ra sao (dẫn số event) |
| Failure mode | Mã FM-xx trong `docs/failure_taxonomy.md` |
| Đối chứng | Cùng claim@seed trên shape `fixed`: bước đó khác thế nào |
| Regression test | Tên test + grader/assert nào bắt được; đã thấy fail trên variant lỗi và pass trên `fixed` chưa |
| Chưa chắc chắn | Điều trace không chứng minh được |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
