from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from backend.app.services.pitcher_prediction_service import PitcherPredictionService

router = APIRouter(prefix="/pitcher-prediction", tags=["Pitcher Prediction"])

# Initialize service
pitcher_prediction_service = PitcherPredictionService()


# ===== Request/Response Schemas =====

class WhiffPredictionRequest(BaseModel):
    """Whiff率予測リクエストスキーマ"""
    pitcher_name: str = Field(..., description="投手名 (例: 'Yamamoto, Yoshinobu')")
    batter_stand: Optional[str] = Field(None, description="打者の左右 ('L' or 'R', null=指定なし)")
    inning: Optional[int] = Field(None, description="イニング (1-9, null=指定なし)", ge=1, le=9)
    order_thru: Optional[int] = Field(None, description="打順巡目 (1-3, null=指定なし)", ge=1, le=3)
    runner_situation: Optional[str] = Field(None, description="ランナー状況 ('other', 'risp', 'bases loaded', null=指定なし)")
    batter_level: Optional[str] = Field(None, description="打者レベル ('super elite', 'elite', 'great', 'average', 'below average', null=指定なし)")
    count_situation: Optional[str] = Field(None, description="カウント状況 ('pitcher_advantage', 'batter_advantage', 'even', null=指定なし)")
    pitch_count_group: Optional[str] = Field(None, description="球数グループ ('1-35', '36-69', '70-99', '100+', null=指定なし)")


class PitchTypeWhiffPrediction(BaseModel):
    """球種別のwhiff率予測"""
    pitch_name: str = Field(..., description="球種名")
    predicted_whiff_rate: float = Field(..., description="予測whiff率")
    actual_whiff_rate: Optional[float] = Field(None, description="実際のwhiff率")
    pitch_count: Optional[int] = Field(None, description="投球数")


class WhiffPredictionResponse(BaseModel):
    """Whiff率予測レスポンススキーマ"""
    pitcher_name: str
    situation: dict
    predictions: List[PitchTypeWhiffPrediction]
    recommendations: List[str]


# ===== API Endpoints =====

@router.post("/predict-whiff", response_model=WhiffPredictionResponse)
async def predict_whiff_rate(request: WhiffPredictionRequest):
    """
    投手の状況別whiff率を予測

    指定された状況（カウント、打者レベル、イニング等）における
    各球種のwhiff率を予測し、攻略ポイントを提示します。
    """
    try:
        result = await pitcher_prediction_service.predict_whiff(
            pitcher_name=request.pitcher_name,
            batter_stand=request.batter_stand,
            inning=request.inning,
            order_thru=request.order_thru,
            runner_situation=request.runner_situation,
            batter_level=request.batter_level,
            count_situation=request.count_situation,
            pitch_count_group=request.pitch_count_group
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"予測エラー: {str(e)}")


@router.get("/pitchers", response_model=List[str])
async def get_available_pitchers():
    """
    予測可能な投手一覧を取得
    """
    try:
        pitchers = await pitcher_prediction_service.get_available_pitchers()
        return pitchers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"投手一覧取得エラー: {str(e)}")
