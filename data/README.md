# 데이터셋 출처 및 사용 안내
- 원본: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- 제공: Olist, 2016–2018 브라질 익명화 주문 데이터
- 라이선스: CC BY-NC-SA 4.0 (비영리 이용, 저작자표시, 동일조건변경허락)
- 원본 파일은 저장소에 재배포하지 않습니다. 원본 출처에서 CSV를 내려받아 **data/raw/** 아래에 저장하세요. 기본 실행에는 아래 8개 파일이 필요합니다.
- 필수 파일: olist_orders_dataset.csv, olist_customers_dataset.csv, olist_order_items_dataset.csv, olist_order_payments_dataset.csv, olist_order_reviews_dataset.csv, olist_products_dataset.csv, product_category_name_translation.csv.
- 위치 좌표 분석은 추가로 olist_geolocation_dataset.csv를 사용하며 현재 기본 분석에서는 사용하지 않습니다.

## 주의
- `customer_id`는 주문별 고객 ID이며 재구매 분석에는 `customer_unique_id`를 사용합니다.
- 결제와 상품은 주문당 여러 행이므로 각각 **주문 단위로 집계한 뒤** 병합합니다.
- `payment_value`는 결제금액, `price`는 상품가격으로 정의가 다릅니다.
- 방문/클릭/장바구니 이벤트가 없어 실제 사이트 전환 퍼널은 계산할 수 없습니다.
