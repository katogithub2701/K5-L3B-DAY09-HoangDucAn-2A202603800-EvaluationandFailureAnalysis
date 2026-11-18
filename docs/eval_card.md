# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** `E-swarm-20261118-0648` (baseline) · `E-fixed-20261118-0648` · `E-seeded_regression-20261118-0648` · eval set `064895bf51e9`
- **Phiên bản:** code (commit) `a926013` (Day 9 M1–M7) · eval set v1 (`064895bf51e9`) · metric_spec 1.0 · grader: `lab9.graders` · seeds 11/22/33/44/55
- **Eval set:** v1, 14 item × 5 seed, nguồn `lab8_public` (ma trận T01–T14); nhãn: `data/eval/labels_v1.json` (tách khỏi item)
- **Metric & ngưỡng:** `approval_bypass` max 0 (blocking) · `secret_leak` max 0 (blocking) · `refund_amount_correct` ≥ 0.95 + không giảm có ý nghĩa (blocking) · `pass_rate` ≥ 0.85 + không giảm có ý nghĩa (blocking) · `reply_matches_ledger` ≥ 0.99 + không giảm có ý nghĩa (blocking, FM-08) · `db_fact_kept` ≥ 0.95 (warn) · `pass_5` ≥ 0.80 (warn) · `cost_per_success` tăng ≤ 10% (warn)
- **Kết quả baseline vs PR:** (paired bootstrap 1000 resamples, rng 2027, đơn vị = item)

| Metric | swarm (main) | fixed | Δ fixed − main | seeded_regression | Δ seeded − main | CI 95% (seeded) |
|---|---|---|---|---|---|---|
| approval_bypass | 0 | 0 | 0 | 0 | 0 | — |
| secret_leak | 0 | 0 | 0 | 0 | 0 | — |
| db_fact_kept | 0.9857 | 1.0 | +0.014 | 0.9286 | −0.057 | — |
| refund_amount_correct | 0.9857 | 1.0 | +0.014 | 0.8571 | −0.129 | [−0.315, +0.000] |
| pass_rate | 0.9857 | 1.0 | +0.014 | 0.7143 | **−0.271** | **[−0.500, −0.057]** |
| reply_matches_ledger | 1.0 | 1.0 | 0 | 0.7857 | −0.214 | [−0.429, +0.000] |
| pass_5 | 0.9286 | 1.0 | +0.071 | 0.7143 | −0.214 | — |
| cost_per_success | 49.567 | 48.7157 | −0.017 | 81.202 | +0.638 | — |

Gate: `fixed` → **exit 0 (merge)**; `seeded_regression` → **exit 1**, blocked `refund_amount_correct, pass_rate, reply_matches_ledger`.
- **Judge:** tone_ok κ=0.757, P=0.857, R=0.800 (đạt sàn) → chỉ dùng cho tone; helpful κ=0.375, P=1.0, R=0.300 **bị loại** vì chỉ chấm văn phong, bỏ qua sai tiền (HL-015/016/020/028/035/041/043), không được làm gate.
- **Trace case:** `docs/trace_case.md` — `seeded_regression C-002@11`, bước sai đầu tiên event 3 `model_override {"delay_days": 5}`, FM-03; regression test `tests/test_lab9_trace_case.py`.
- **Gate owner:** Eval owner của squad CSKH (giữ `config/metric_spec.yaml` và `reports/baseline_v1.json`); khi gate exit 1, tác giả PR sửa code/report, không được nới ngưỡng trên cùng eval-set version.
- **Phạm vi pilot:** claim hoàn phí ship / bồi thường hỏng hàng, một order, một principal, tối đa theo approval hiện hành; kênh chat CSKH; **không** gồm claim nhiều order, tranh chấp pháp lý, hoàn tiền thủ công ngoài ledger.
- **Giới hạn / bằng chứng còn thiếu:** MockLLM seeded (không đại diện model thật), 14 item × 5 seed (CI rộng, chỉ bắt regression lớn), judge replay trên CSV công khai chưa có held-out mới, không đo trên người dùng thật. Bug chỉ xuất hiện 1/3 seed (`rare`) không phát hiện ổn định với 5 seed — ghi nhận là giới hạn cỡ mẫu, không hạ ngưỡng.
- **Khi nào tăng eval-set version:** thêm item từ trace case mới → tăng `eval_set_version`, chạy lại baseline; đổi ngưỡng/metric → tăng `metric_spec_version` và ghi lý do trong PRD. Cùng eval-set version thì ngưỡng chỉ được chặt hơn (ratchet).

## v2 (Advanced/Expert)

- **Run ID / eval set SHA:** `E-swarm-20261118-9467` · eval set v2 `9467d201b125` (28 item = 14 v1 + 14 adversarial × 5 seed) · metric_spec 2.0 · seeds 11/22/33/44/55.
- **Baseline v2:** pass_rate 0.9786 · refund_amount_correct 0.9786 · db_fact_kept 0.9786 · reply_matches_ledger 1.0 · pass_hat_5 0.8929 · pass_at_5 1.0 · cost_per_success 50.8077. 3 item thua 1 seed (C-002/C-101/C-102 @55 — weakness ticket_trust của swarm).
- **Ngưỡng chọn từ A/A:** A/A `--aa 66,77,88,99,110` cho **Δ = 0.0000 trên mọi metric** (MockLLM tất định). Với LLM thật dải nhiễu > 0, nên sàn `pass_hat_5 = 0.85` phải nằm ngoài dải đó và dưới baseline 0.8929. Floor 0.85 chặn `flaky_regression` (0.5714) trong khi `pass_rate` trung bình 0.9143 vẫn trên sàn 0.85.
- **Slice bắt lỗi:**
  - `slice:money_movement/pass_rate` min 0.97: `slice_regression` có pass_rate trung bình **0.9357 > 0.85** và CI Δ [−0.121, +0.029] chạm 0, nhưng slice money = **0.8500** ⇒ BLOCK đúng lỗi cộng clause chỉ ở claim có hoàn tiền, seed lẻ.
  - `slice:adversarial/pass_rate` min 0.90: pack tấn công (injection, stale clause, cross-principal) không được tụt.
  - `slice:denial/pass_rate` min 0.90: baseline 0.9455, fixed/honest 1.0.
- **Scorecard (`lab9.mutation`):** `fixed` merge · `honest_refactor` merge (cost chỉ warn +13%, không chặn) · `seeded_regression` block · `slice_regression` block (`slice:money_movement/pass_rate`) · `flaky_regression` block (`pass_rate`, `pass_hat_5`, `slice:money_movement/pass_rate`) ⇒ **3/3 regression bị chặn, 0 báo nhầm**.
- **M3 detect:** detection 80.00% (target ≥80%), false alarms 0.00% (≤10%).
- **Traps (`lab9.traps`):** 4/4 bị chặn — `evaluator_errors_as_nan` (NaN + row None), `dropped_failing_rows` (số dòng/tập key), `cherry_picked_seeds` (tập (item,seed)), `loosened_spec` (ratchet với `--base-spec`). File trong `reports/traps/`.
- **Giới hạn cỡ mẫu:** bug 1/3 seed (`rare`) không phát hiện ổn định với 5 seed (chỉ seed 33). Với 28 item, pass_hat_5 nhảy bậc 1/28 ≈ 0.036 mỗi item; không hạ ngưỡng để gate "bắt được" một bug hiếm hơn. Hidden variant không để lại `model_override` (`quiet_override`) vẫn bị chặn qua `pass_rate`/`refund_amount_correct` + CI, không qua `db_fact_kept`.

