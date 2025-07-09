import pandas as pd #data 다루기 쉽게 해주는 library

# 1. CSV 파일 읽기
df = pd.read_csv("Mars_Base_Inventory_List.csv") #df는 dataframe의 약자로 변수/read_csv()는 pandas의 함수/경로 입력

# 2. Flammability 열을 숫자형(float)으로 변환 (숫자가 아닌 값은 NaN으로 처리)
df["Flammability"] = pd.to_numeric(df["Flammability"], errors="coerce") #[ ]는 특정 column 선택/ 불러온 df에 적용한 것 덮어씌우는 과정. 원본 파일은 훼손X

# 3. NaN 제거 (인화성 정보 없는 행 제거)
df = df.dropna(subset=["Flammability"]) #subset는 지울 때 기준이 될 열을 지정하는 공식 이름(키워드). 변경 불가.

# 4. 인화성 기준으로 내림차순 정렬
df_sorted = df.sort_values(by="Flammability", ascending=False) #by= 는 기준 열 설정하는 것/	ascending=True면 오름차순 (작은 값 → 큰 값), False면 내림차순 (큰 값 → 작은 값)

# 5. 인화성 ≥ 0.7인 항목만 필터링
danger_df = df_sorted[df_sorted["Flammability"] >= 0.7] #조건에 맞는 행들만 골라내서 새로운 df를 만듬

# 6. 위험 물질만 별도 CSV 파일로 저장
danger_df.to_csv("Mars_Base_Inventory_danger.csv", index=False) #index=false는 행번호 저장 안하겠다는 뜻

# 7. 출력 (옵션)
print("📦 전체 목록:")
print(df)

print("\n🔥 인화성 순 정렬:")
print(df_sorted)

print("\n🚨 인화성 0.7 이상 위험 물질:")
print(danger_df)

print("\n💾 위험 물질 리스트 저장 완료: Mars_Base_Inventory_danger.csv")