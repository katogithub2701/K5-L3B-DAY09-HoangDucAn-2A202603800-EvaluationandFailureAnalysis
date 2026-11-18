# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có (24/4/6/66) | **dùng** cho tiêu chí tone (không dùng để chấm tiền) |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không (κ, R dưới sàn) | **loại** — không được dùng làm gate |

Rogan–Gladen: tone quan sát 0.28 → hiệu chỉnh 0.30; helpful quan sát 0.09 → hiệu chỉnh 0.30.
Judge helpful bắt được rất ít lỗi thật (R=0.3) dù không báo nhầm (P=1.0): nó chỉ nhìn "giọng văn có lịch sự/đầy đủ không", không đọc ledger.

## ≥5 case audit thủ công

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú / sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 `Em đã hoàn tiền cho anh rồi nha…` | PASS | FAIL | **Người** | Judge thấy "thân thiện"; rubric tone phải cấm đại từ `em` với khách và từ đệm `nha` khi thông báo tiền. Thêm ví dụ âm vào rubric. |
| 2 | H-017 `Dạ, bạn ơi… rồi nha` | PASS | FAIL | **Người** | Xưng `bạn` với khách lớn tuổi + `nha`. Rubric phải chấm vai vế (anh/chị), không chỉ "có Dạ". |
| 3 | H-029 `…không cần nhắn thêm.` | PASS | FAIL | **Người** | Câu mệnh lệnh/ra lệnh cho khách. Judge chỉ bắt `Dạ, vui lòng`. Thêm tiêu chí "không ra lệnh, không từ chối trách nhiệm". |
| 4 | H-042 `Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ.` | FAIL | PASS | **Người** | Judge phạt vì "thiếu xin lỗi". Rubric tone không được bắt buộc xin lỗi trong câu trả lời ngắn; chỉ cấm xúc phạm/đùa cợt. |
| 5 | H-051 `Dạ, LogiX đã refund 90.000đ…` | FAIL | PASS | **Người** | Judge phạt từ tiếng Anh `refund`; CS LogiX cho phép. Thêm whitelist thuật ngữ song ngữ vào rubric. |
| 6 | H-063 `…và sẽ hoàn thêm cho anh/chị ạ.` | PASS | FAIL | **Người** | Hứa khoản hoàn ngoài ledger = sai sự thật. Rubric phải tách "tone" khỏi "cam kết số tiền"; đây là lý do dùng code grader cho tiền, không dùng judge. |
| 7 | H-070 `…ạ 😂😂` | PASS | FAIL | **Người** | Emoji trong ngữ cảnh khiếu nại. Thêm luật cấm emoji/telex cười. |
| 8 | H-081 `Dạ, đơn O-107 chưa đủ điều kiện hoàn…` | FAIL | PASS | **Judge** | Nhãn người sai: đọc nhầm ticket; câu trả lời đúng chính sách và đúng tone. **Sửa nhãn người** thành PASS thay vì sửa rubric. |
| 9 | HL-015 `…hoàn 55.000đ` (ledger 40.000đ) | PASS | FAIL | **Người** | Judge helpful không đọc ledger nên bỏ qua sai tiền. Không thể dùng làm gate; correctness do `reply_matches_ledger` (code) chấm. |
| 10 | HL-047 `Ok bạn, đơn O-515 xử lý rồi nhé.` | PASS | FAIL | **Người** | Thiếu thông tin số tiền + xưng hô suồng sã. Rubric helpful phải yêu cầu nêu kết quả/ledger và vai vế. |

## Kết luận
- `helpful` bị loại: κ=0.375 < 0.6 và recall=0.3 < 0.7. Nó là bộ phân loại "văn phong" chứ không phải "đúng/sai nghiệp vụ"; dùng làm gate sẽ cho qua các câu trả lời sai tiền (HL-015/016/020/028/035/041/043).
- `tone_ok` đủ sàn để dùng **có giới hạn** cho tiêu chí tone. Các lỗi còn lại (4 FP ở H-042/H-051/H-081 và 3 FN ở H-008/H-017/H-029) đã được xử lý bằng cách siết rubric như bảng trên.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật. Không dùng judge cho tiền/approval — hai loại đó luôn chấm bằng code.
