import psycopg2, os
import pandas as pd
import numpy as np
import datetime
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

data_updated = False


def set_data_updated():
    global data_updated
    data_updated = True


def pre_processing():
    # 데이터베이스 연결
    con = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT"),
    )
    cur = con.cursor()
    cur.execute(
        "SELECT id, info_name, start_date, end_date, svstatus From exhibitions_exhibition"
    )
    cols = [column[0] for column in cur.description]

    # 데이터프레임 생성
    exhibition_df = pd.DataFrame.from_records(data=cur.fetchall(), columns=cols)

    # 데이터베이스 연결 종료
    con.close()

    # info_name별 유사도 측정
    count_vect = CountVectorizer(min_df=0, ngram_range=(1, 2))
    info_name_mat = count_vect.fit_transform(exhibition_df["info_name"])

    # 유사도 행렬 생성
    info_name_sim = cosine_similarity(info_name_mat, info_name_mat)

    # 데이터 프레임 작업 후에는 data_updated 변수를 False로 바꿔줌
    global data_updated
    data_updated = False

    return exhibition_df, info_name_sim


exhibition_df, info_name_sim = pre_processing()


# 비슷한 전시 추천 시스템 함수
def recommendation(id, top_n=5):
    # 전역변수를 참조하도록 지정함
    global exhibition_df
    global info_name_sim
    global data_updated

    if data_updated:
        exhibition_df, info_name_sim = pre_processing()

    # 입력한 정보의 index
    target = exhibition_df[exhibition_df["id"] == id]
    target_index = target.index.values

    # 데이터프레임에 입력한 정보의 유사도 추가
    exhibition_df["similarity"] = info_name_sim[target_index, :].reshape(-1, 1)

    # start_date가 오늘 날짜 이전이거나 오늘이고, end_date가 오늘 날짜거나 오늘 날짜 이후인 데이터만 추출하기
    today = datetime.date.today()
    period = (exhibition_df["start_date"] <= today) & (
        exhibition_df["end_date"] >= today
    )
    filterd_exhibition_df = exhibition_df.loc[period].sort_values(
        by=["end_date"], ascending=True
    )

    # 날짜 필터링 된 데이터프레임의 유사도 내림차순 정렬
    temp = filterd_exhibition_df.sort_values(by=["similarity"], ascending=False)
    # 자기 자신 제거
    temp = temp[temp.index.values != target_index]
    # svstatus가 접수중인 데이터만 추출
    temp = temp[temp["svstatus"] == "접수중"]

    # 데이터프레임 기준 최종 유사도 Top5 index 리스트
    final_index = temp.index.values[:top_n]

    # 최종 유사도 Top5의 데이터프레임
    raw_exhibitions = filterd_exhibition_df.loc[final_index]

    # 최종 유사도 Top5의 데이터베이스 상 id 리스트
    ml_recommend_exhibitions_id_list = np.array(raw_exhibitions[["id"]]["id"].tolist())

    return ml_recommend_exhibitions_id_list
