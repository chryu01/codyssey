mport csv

# 1. CSV 파일 읽고 출력
with open("Mars_Base_Inventory_List.csv", mode="r", encoding="utf-8") as file:
    reader = csv.reader(file)  #file의 한줄씩 csv.reader로 읽음. 그 읽은 내용 reader라는 변수에 저장
    header = next(reader)  # 첫 줄 (헤더)/['이름','수량','인화성']과 같은 list가 저장됨/데이터가 아니기 때문에 따로 꺼내서 저장하는 것
    data = list(reader)    # 나머지 줄들

print("📦 전체 목록:") #csv파일 본격적으로 출력
print(header)
for row in data:
    print(row)


# 2. 리스트 객체로 변환
inventory = []

for row in data:
    # Weight와 Specific Gravity는 float로 변환 시도 → 안 되면 None
    try:
        weight = float(row[1])
    except ValueError:
        weight = None  # 또는 'Unknown'

    try:
        gravity = float(row[2])
    except ValueError:
        gravity = None  # 또는 'Unknown'

    try:
        flammability = float(row[4])
    except ValueError:
        flammability = None  # 하지만 지금 파일엔 다 숫자임

    item = {
        "Substance": row[0],  #어차피 str이기 때문에 따로 try/except 정의해줄 필요 X + list 안에 있는 데이터의 첫번째는 0번째라고 함.
        "Weight(g/cm3)": weight,
        "Specific Gravity": gravity,
        "Strength": row[3], #어차피 str이기 때문에 따로 try/except 정의해줄 필요 X
        "Flammability": flammability
    }
    inventory.append(item)  #변수 inventory는 item이라는 dictionary를 모은 list가 되는 것.


# 3. 인화성이 높은 순으로 정렬
inventory_sorted = sorted(inventory, key=lambda x: x["Flammability"], reverse=True) #item은 dict인데, "Flammability"라는 키값을 선택하고 그것을 기준으로 정렬하기. 큰 것부터 정렬하기 위해 reverse=True

print("\n🔥 인화성 높은 순 정렬:")
for item in inventory_sorted: #정렬된 새 list의 item들 출력
    print(item)

# 4. 인화성 지수 0.7 이상만 추출
danger_items = [item for item in inventory_sorted if item["Flammability"] >= 0.7]  #"inventory_sorted 안에 있는 item 중에서, item["Flammability"] 값이 0.7 이상인 것만 골라서 새로운 리스트인 danger_items에 담아달라는 의미

'''
danger_items = []
for item in inventory_sorted:
    if item["Flammability"] >= 0.7:
        danger_items.append(item)
'''

print("\n🚨 인화성 0.7 이상 위험 물질:")
for item in danger_items:
    print(item)

    
# 5. 위험 물질을 CSV로 저장
output_file = "Mars_Base_Inventory_danger.csv"
with open(output_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Substance", "Weight(g/cm3)", "Specific Gravity", "Strength","Flammability"])  # 헤더
    for item in danger_items:
        writer.writerow([item["Substance"], item["Weight(g/cm3)"], item["Specific Gravity"], item["Strength"],item["Flammability"]])

print(f"\n💾 위험 물질 리스트를 '{output_file}' 파일로 저장 완료!")