from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 1. 사업 공고리스트 API (사업공고문 DB -> 웹 UI, 서버)
@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    """
    사업 공고 목록을 조회
    - DB에서 조회한 데이터를 웹에 표시 (중복체크를 아직 못한 상태 이건 좀더 고민)
    - 서버에서는 중복체크 및 벡터 값으로 저장하기 위해서 가져와야 함
    """
    try:
        # DB에서 공고 데이터 조회
        announcements = {
            'title': '공고 제목',
            'contents': '공고 내용',
            'url': '공고 URL',
            'submit_period': '접수기간'
        }
        
        # 1. 웹 UI에 데이터 전달
        # 2. 서버에서 벡터 처리 및 저장
        return announcements
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

# 2. 기업고객정보 API (고객 DB -> 서버)
@app.route('/api/company', methods=['GET'])
def get_company_info():
    """
    기업 정보를 조회합니다.
    Query Parameters:
    - company_name: 기업명
    - company_id: 기업ID
    - address: 주소
    """
    try:
        # 알파에듀 고객 DB에서 기업 정보 조회
        company_info = {
            'business_type': '사업분야',
            'company_name': '기업명',
            'company_id': '기업ID',
            'address': '주소',
            'proposal_status': '(회사소개서 pdf)'  # 회사소개서는 옵션임
        }

        # 백엔드 내부에서 사용할 데이터만 반환
        return company_info  
    
    except Exception as e:
        print(f"Error in get_company_info: {str(e)}")
        return None  # 에러 발생시 None 반환

# 3. 제안서 작성 버튼 상태 전달 API (웹 UI -> 서버)
@app.route('/api/proposal-status', methods=['POST'])
def update_proposal_status():
    """
    제안서 작성 버튼 눌렀을 때
    내부적으로 기업정보를 조회하여 모델로 전달
    """
    try:
        # 1. 버튼 클릭 정보 받기
        data = request.get_json()
        company_id = data.get('company_id')
        
        # 2. 서버 내부에서 기업정보 조회
        # company_id를 사용하여 기업정보 DB에서 조회
        company_info = get_company_info()  
        
        if company_info is None:
            # 확인용
            print("Error: 기업 정보 조회 실패")
            return None
            
        # 3. 제안서 작성 모델에 전달할 데이터 구성
        # 이름 나중에 수정
        model_input = {
            'button_status': data.get('button_status'),
            'announcement_number': data.get('announcement_number'),
            'business_type': company_info.get('business_type'),
            'company_name': company_info.get('company_name'),
            'address': company_info.get('address'),
            'proposal_status': company_info.get('proposal_status')
        }
        
        # 4. 제안서 작성 모델로 전달
        return model_input
    
    except Exception as e:
        print(f"Error in proposal button: {str(e)}")
        return None


# 4. 제안서 API (서버 -> 웹 UI)
@app.route('/api/proposals', methods=['GET'])
def get_proposal():
    """
    모델이 생성한 제안서를 반환함
    Request Parameters: (GET 메소드므로 쿼리 파라미터로 변경)
    - company_id: 기업ID
    - announcement_number: 공고일련번호
    """
    try:
        # GET 메소드는 request.args로 파라미터를 받음
        company_id = request.args.get('company_id')
        announcement_number = request.args.get('announcement_number')
        
        # 모델에서 생성된 제안서 정보 반환
        proposal_response = {
            'company_id': company_id,
            'announcement_number': announcement_number,
            'proposal_content': 'LLM 모델이 생성한 제안서 내용',
            'created_date': '생성일자',
        }
        
        return jsonify(proposal_response), 200
        
    except Exception as e:
        print(f"Error in getting proposal: {str(e)}")
        return jsonify({'error': '제안서 생성 실패'}), 500

# 5. 추천 버튼 상태 전달 API (웹 UI -> 서버)
@app.route('/api/recommendation-status', methods=['POST'])
def update_recommendation_status():
    """
    추천 버튼 눌렀을 때
    내부적으로 기업정보를 조회하여 모델로 전달
    """
    try:
        # 1. 버튼 클릭 정보 받기
        data = request.get_json()
        company_id = data.get('company_id')
        
        # 2. 서버 내부에서 기업정보 조회
        # company_id를 사용하여 기업정보 DB에서 조회
        company_info = get_company_info()  
        
        if company_info is None:
            # 확인용
            print("Error: 기업 정보 조회 실패")
            return None
            
        # 3. 추천 모델에 전달할 데이터 구성
        # 이름 나중에 수정
        model_input = {
            'button_status': data.get('button_status'),
            'business_type': company_info.get('business_type'),
            'company_name': company_info.get('company_name'),
            'address': company_info.get('address')
        }
        
        # 4. 사업공고문 추천 모델로 전달
        return model_input
    
    except Exception as e:
        print(f"Error in recommendation button: {str(e)}")
        return None

# 6. 추천 공고 API (서버 -> 웹 UI)
@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """
    모델이 추천한 공고 목록을 반환함
    Request Parameters:
    - company_id: 기업ID
    - announcement_number: 공고일련번호
    """
    try:
        # GET 메소드에서는 request.args를 사용하여 쿼리 파라미터를 받음
        company_id = request.args.get('company_id')
        announcement_number = request.args.get('announcement_number')
        
        # 모델에서 생성된 추천 공고 정보 반환
        recommendations = {
            'company_id': company_id,
            'announcement_number': announcement_number,
            # LLM 모델이 제시한 추천 사유를 할지, 아니면 규칙 기반처럼 해야할지 고민이네
            'recommendation_reason': '추천사유(지역, 분야...)',
            'recommended_date': '추천일자'
        }
        return jsonify(recommendations), 200
        
    except Exception as e:
        print(f"Error in getting recommendations: {str(e)}")
        return jsonify({'error': '추천 공고 조회 실패'}), 500
    

@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)