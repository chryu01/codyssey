import numpy as np

# 1. CSV 파일 읽기 (dtype을 명시)
#dtype=[(열, 타입),(열, 타입)] 
dtype = [('parts', 'U20'), ('strength', 'f8')] #unicode는 문자열(한국어도 포함) 뒤에 숫자는 몇글자까지 가능한지./f는 float로 실수

#genfromtxt는 txt파일을 배열로 바꾸는 함수(loadtxt와는 다르게 문자형/숫자형/빈칸 읽기 가능)
#delimiter는 구분 기준, skip_header=1에서 1은 그 줄부터 읽으라는 뜻. 앞 스킵하고 지정한 줄 번호의 데이터부터 읽기
#dtype=dtype: 열 이름과 자료형을 명확히 정의한 걸 genfromtxt에 전달
arr1 = np.genfromtxt('mars_base_main_parts-001.csv', delimiter=',', skip_header=1, encoding='utf-8-sig', dtype=dtype) 
arr2 = np.genfromtxt('mars_base_main_parts-002.csv', delimiter=',', skip_header=1, encoding='utf-8-sig', dtype=dtype)
arr3 = np.genfromtxt('mars_base_main_parts-003.csv', delimiter=',', skip_header=1, encoding='utf-8-sig', dtype=dtype)

# 2. 배열 합치기 (concatenate 사용)
#구조화 배열은 사실상 dict와 같은 구조. vstack은 일반 2차원배열로 변환시키려 하며 열 이름을 무시하거나 axis기준이 잘못될 수 있음->concatenate가 더 적합함
parts = np.concatenate((arr1, arr2, arr3))

# 3. 부품별 평균값 계산
#np.unique()는 중복없는 고유 이름만 추출
#parts['parts']에서 앞의 parts는 위에서 합쳐놓은 전체 배열을 의미. 뒤의 대괄호 안의 'parts'는 맨위의 dtype에서 정의한 열 이름
unique_parts = np.unique(parts['parts'])

#평균이 낮은 재료들의 이름과 평균값을 각각 저장할 빈 리스트
low_parts = []
low_means = []

#parts['parts']==part: 재료가 어떤 행에 있는지 표시하는 마스크를 만듦
#parts['strength'][]: 위에서 만든 마스크가 True인 행만 선택
for part in unique_parts:
    strength_values = parts['strength'][parts['parts'] == part]
    mean_strength = np.mean(strength_values)
    if mean_strength < 50:
        low_parts.append(part) #.append의 경우 그냥 맨 뒤에 하나씩 추가하는 것
        low_means.append(mean_strength)

# 4. 저장할 배열 생성
#np.array(..., dtype=...): 구조화 배열 생성
#zip(low_parts,low_means)는 두 리스트를 하나씩 tuple로 묶어줌/tuple은 값 변경이 불가
'''
zip()은 한번만 사용 가능한 zip object
즉, zip(a, b)	튜플 묶음 객체 (보이지 않음, 반복문에만 사용 가능)
list(zip(a, b))	튜플들을 담은 리스트 (즉시 볼 수 있고 활용 가능)
'''
#dtype을 만들 때, 이제는 평균 값을 정의한 것이기 때문에 후자의 열 이름을 'average_strength'로 설정한 것
output_array = np.array(list(zip(low_parts, low_means)), dtype=[('parts', 'U20'), ('average_strength', 'f8')])

# 5. 파일 저장 (예외 처리 포함)
#fmt는 format이라는 뜻. 각각 문자형+float는 소수 3자리까지 표현하겠다는 의미
try:
    np.savetxt('parts_to_work_on.csv', output_array, delimiter=',', fmt='%s,%.3f', header='parts,average_strength', comments='')
    print('✅ parts_to_work_on.csv 저장 완료.')
except Exception as e:
    print('⚠️ 파일 저장 중 오류 발생:', e)