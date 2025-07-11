# design_dome.py

# 전역 변수, 초기화시켜놓은 상태
material = ''
diameter = 0
thickness = 1
area = 0
weight = 0

def sphere_area(diameter, material='glass', thickness=1):
    global area, weight #전역변수로 설정

    # 반지름 구하기 (지름의 반)
    radius = diameter / 2

    # 반구 표면적 (2 * π * r^2)
    area = 2 * 3.1415926535 * (radius ** 2)

    # 면적 단위 변환: m^2 → cm^2 (1m^2 = 10000cm^2)
    area_cm2 = area * 10000

    # 재질 밀도 (g/cm³)
    if material == 'glass':
        density = 2.4
    elif material == 'aluminum':
        density = 2.7
    elif material == 'steel':
        density = 7.85
    else:
        print('지원하지 않는 재질입니다. 기본값 유리로 계산합니다.')
        density = 2.4
        material = 'glass'

    # 부피 = 면적 * 두께 (cm³)
    volume_cm3 = area_cm2 * thickness #얇은 반구 껍질의 재료 부피이기에 일반적 반구 부피 구하는 식과 다름

    # 무게 (g) = 부피 * 밀도
    weight_g = volume_cm3 * density

    # g → kg
    weight_kg = weight_g / 1000

    # 화성 중력 적용 (약 0.38배)
    weight_kg_mars = weight_kg * 0.38

    # 전역 변수에 저장, round(숫자, 자리수): 자리수까지 반올림
    weight = round(weight_kg_mars, 3)
    area = round(area, 3)

    return area, weight


# 반복 실행
while True:
    print('\n돔 무게 계산기 (종료하려면 "exit" 입력)\n')

    diameter_input = input('지름 (m): ')
    if diameter_input.strip().lower() == 'exit': #대문자/소문자로 exit 입력시 끝
        break
        #else가 없는 이유는 if문 충족시 break가 돼서 try/except가 실행될 염려가 없기 때문.
    try:
        diameter = float(diameter_input) #들어온 값을 float로 변환해서 위에 정의한 diameter라는 전역변수에 넣어줌
        if diameter <= 0:
            print('지름은 0보다 커야 합니다.')
            continue #While true 이후의 input으로 돌아가서 다시 실행
    except ValueError:
        print('숫자를 입력해 주세요.')
        continue

    material_input = input('재질 (glass / aluminum / steel) [기본값: glass]: ').strip().lower() #대문자로 들어와도 같은 것으로 인식하기 위해
    if material_input == '':
        material_input = 'glass' #아무것도 입력X->glass로 생각
    if material_input not in ['glass','aluminum','steel']: #elif가 아닌 이유: 위의 조건과 배타적이지 않기 때문??
        print('지원하지 않는 재질입니다. 기본값 glass로 설정합니다.')
        material_input = 'glass'
    material = material_input #전역변수에 값 입력

    thickness_input = input('두께 (cm) [기본값: 1]: ').strip() #.strip()은 공백을 제거하는 함수
    if thickness_input == '':
        thickness = 1   #아무것도 입력하지 않으면 1로 설정
    else:   #else가 없다면 try/except도 실행되어 에러가 발생할 수 있음
        try:
            thickness = float(thickness_input)
            if thickness <= 0:
                print('두께는 0보다 커야 합니다. 기본값 1 사용.')
                thickness = 1
        except ValueError:
            print('숫자가 아닌 값입니다. 기본값 1 사용.')
            thickness = 1

    # 함수 호출
    area, weight = sphere_area(diameter, material, thickness)

    # 결과 출력
    print(f'재질 ⇒ {material}, 지름 ⇒ {diameter}, 두께 ⇒ {thickness}, 면적 ⇒ {area}, 무게 ⇒ {weight} kg') #print문의 ()안에 변수 지정 바로 해주기 위해 따옴표 앞에 f 사용

print('\n프로그램을 종료합니다.')
 
