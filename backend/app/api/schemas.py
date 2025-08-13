from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# PyDantic model for players information
class PlayerBasicInfo(BaseModel):
    """
    選手情報を表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    mlb_id: int = Field(..., description="MLB選手ID")
    bbref_id: Optional[str] = Field(None, description="選手のBBRef ID")
    idfg: Optional[int] = Field(None, alias="fangraphs_id", description="選手ID（FanGraphs）")
    first_name: str = Field(..., description="選手の名")
    last_name: str = Field(..., description="選手の姓")
    mlb_debut_year: Optional[int] = Field(None, description="MLBデビュー年")
    mlb_last_year: Optional[int] = Field(None, description="MLB最終年")
    full_name: Optional[str] = Field(None, description="選手フルネーム")


# Pydantic model for Shohei Ohtani's two-way stats
class ShoheiOhtaniTwoWayStats(BaseModel):
    """ Shohei Ohtaniの二刀流成績を表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    batter_mlb_id: int = Field(..., description="Shohei Ohtaniの打者MLB ID")
    pitching_game_date: Optional[datetime] = Field(None, description="投手としての試合日")
    pitching_game_batting_date: Optional[datetime] = Field(None, description="二刀流としての試合日")
    hits: Optional[int] = Field(None, description="登板日の安打数")
    home_runs: Optional[int] = Field(None, description="登板日の本塁打数")
    triples: Optional[int] = Field(None, description="登板日の三塁打数")
    doubles: Optional[int] = Field(None, description="登板日の二塁打数")
    singles: Optional[int] = Field(None, description="登板日の単打数")
    walks_and_hbp: Optional[int] = Field(None, description="登板日の四球と死球数")
    at_bats: Optional[int] = Field(None, description="登板日の打席数")
    numerator_for_obp: Optional[int] = Field(None, description="登板日の出塁率計算の分子")
    denominator_for_obp: Optional[int] = Field(None, description="登板日の出塁率計算の分母")
    batting_average: Optional[float] = Field(None, description="登板日の打率", ge=0.0, le=1.0)
    on_base_percentage: Optional[float] = Field(None, description="登板日の出塁率", ge=0.0, le=1.0)
    slugging_percentage: Optional[float] = Field(None, description="登板日の長打率", ge=0.0, le=5.0)
    on_base_plus_slugging: Optional[float] = Field(None, description="登板日のOPS", ge=0.0, le=5.0)
    next_game_date_for_batter: Optional[datetime] = Field(None, description="次の試合日（打者として）")
    next_game_hits: Optional[int] = Field(None, description="次の試合日の安打数（打者として）")
    next_game_home_runs: Optional[int] = Field(None, description="次の試合日の本塁打数（打者として）")
    next_game_triples: Optional[int] = Field(None, description="次の試合日の三塁打数（打者として）")
    next_game_doubles: Optional[int] = Field(None, description="次の試合日の二塁打数（打者として）")
    next_game_singles: Optional[int] = Field(None, description="次の試合日の単打数（打者として）")
    next_game_walks_and_hbp: Optional[int] = Field(None, description="次の試合日の四球と死球数（打者として）")
    next_game_at_bats: Optional[int] = Field(None, description="次の試合日の打席数（打者として）")
    next_game_numerator_for_obp: Optional[int] = Field(None, description="次の試合日の出塁率計算の分子（打者として）")
    next_game_denominator_for_obp: Optional[int] = Field(None, description="次の試合日の出塁率計算の分母（打者として）")
    next_game_batting_average: Optional[float] = Field(None, description="次の試合日の打率（打者として）", ge=0.0, le=1.0)
    next_game_on_base_percentage: Optional[float] = Field(None, description="次の試合日の出塁率（打者として）", ge=0.0, le=1.0)
    next_game_slugging_percentage: Optional[float] = Field(None, description="次の試合日の長打率（打者として）", ge=0.0, le=5.0)
    next_game_on_base_plus_slugging: Optional[float] = Field(None, description="次の試合日のOPS（打者として）", ge=0.0, le=5.0)


# Pydantic model for season batting stats
class PlayerBattingSeasonStats(BaseModel):
    """
    選手の年度別打撃成績を表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    idfg: int = Field(..., description="選手ID（FanGraphs）")
    season: Optional[int] = Field(None, description="シーズン年")
    name: str = Field(..., description="選手名")
    team: Optional[str] = Field(None, description="所属チーム名")
    league: Optional[str] = Field(None, description="所属リーグ")
    g: int = Field(..., description="出場試合数")
    ab: int = Field(..., description="打席数")
    pa: int = Field(..., description="打数")
    r: int = Field(..., description="得点")
    h: int = Field(..., description="安打数")
    singles: Optional[int] = Field(None, alias="1b", description="一塁打数")
    doubles: Optional[int] = Field(None, alias="2b", description="二塁打数")
    triples: Optional[int] = Field(None, alias="3b", description="三塁打数")
    hr: int = Field(..., description="本塁打数")
    rbi: int = Field(..., description="打点")
    sb: int = Field(..., description="盗塁数")
    bb: int = Field(..., description="四球数")
    so: int = Field(..., description="三振数")
    sf: Optional[int] = Field(None, description="犠飛数")  # Sacrifice Flies
    sh: Optional[int] = Field(None, description="犠打数")  # Sacrifice Hits
    hbp: Optional[int] = Field(None, description="死球数")  # Hit By Pitch
    avg: float = Field(..., description="打率")  # ge: greater than or equal, le: less than or equal
    obp: float = Field(..., description="出塁率", ge=0.0, le=1.0)
    slg: float = Field(..., description="長打率", ge=0.0, le=5.0)  # 長打率は1.0を超えることがあるため、最大値を調整
    ops: float = Field(..., description="OPS", ge=0.0, le=5.0)  # OPSも1.0を超えることがあるため、最大値を調整
    iso: Optional[float] = Field(None, description="ISO")  # Optionalにすることで、データがない場合も対応可能
    babip: Optional[float] = Field(None, description="BABIP", ge=0.0, le=1.0)  # BABIPも0.0から1.0の範囲
    wrcplus: Optional[int] = Field(None, description="wRC+")
    woba: Optional[float] = Field(None, description="wOBA", ge=0.0, le=1.0)  # wOBAも0.0から1.0の範囲
    war: Optional[float] = Field(None, description="fWAR")
    wpa: Optional[float] = Field(None, description="wPA")
    wpa_li: Optional[float] = Field(None, description="wPA/LI")
    hardhitpct: Optional[float] = Field(None, description="Hard Hit Percentage", ge=0.0, le=1.0)  # Hard Hit Percentageも0.0から1.0の範囲
    barrelpct: Optional[float] = Field(None, description="Barrel Percentage", ge=0.0, le=1.0)  # Barrel Percentageも0.0から1.0の範囲
    hits_at_risp: Optional[int] = Field(None, description="RISPでの安打数")  # Runners In Scoring Positionでの安打数
    singles_at_risp: Optional[int] = Field(None, description="RISPでの単打数")  # Runners In Scoring Positionでの単打数
    doubles_at_risp: Optional[int] = Field(None, description="RISPでの二塁打数")  # Runners In Scoring Positionでの二塁打数
    triples_at_risp: Optional[int] = Field(None, description="RISPでの三塁打数")  # Runners In Scoring Positionでの三塁打数
    home_runs_at_risp: Optional[int] = Field(None, description="RISPでの本塁打数")  # Runners In Scoring Positionでの本塁打数
    at_bats_at_risp: Optional[int] = Field(None, description="RISPでの打席数")  # Runners In Scoring Positionでの打席数
    batting_average_at_risp: Optional[float] = Field(None, description="RISPでの打率", ge=0.0, le=1.0)  # Runners In Scoring Positionでの打率
    slugging_percentage_at_risp: Optional[float] = Field(None, description="RISPでの長打率", ge=0.0, le=5.0)  # Runners In Scoring Positionでの長打率


# Pydantic model for batter split stats
class PlayerBattingSplitStats(BaseModel):
    """選手の打撃スプリット成績を表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    idfg: int = Field(..., description="選手ID（FanGraphs）")
    mlb_id: Optional[int] = Field(None, description="MLB選手ID")
    batter_name: str = Field(..., description="選手名")
    game_year: int = Field(..., description="シーズン年")
    team: str = Field(..., description="所属チーム名")
    league: str = Field(..., description="所属リーグ")
    pa: Optional[int] = Field(None, description="打席数")  # Plate Appearances
    # RISP stats
    hits_at_risp: Optional[int] = Field(None, description="RISPでの安打数")  # Runners In Scoring Positionでの安打数
    homeruns_at_risp: Optional[int] = Field(None, description="RISPでの本塁打数")  # Runners In Scoring Positionでの本塁打数
    triples_at_risp: Optional[int] = Field(None, description="RISPでの三塁打数")  # Runners In Scoring Positionでの三塁打数
    doubles_at_risp: Optional[int] = Field(None, description="RISPでの二塁打数")  # Runners In Scoring Positionでの二塁打数
    singles_at_risp: Optional[int] = Field(None, description="RISPでの単打数")  # Runners In Scoring Positionでの単打数
    bb_hbp_at_risp: Optional[int] = Field(None, description="RISPでの四球と死球数")  # Runners In Scoring Positionでの四球と死球数
    so_at_risp: Optional[int] = Field(None, description="RISPでの三振数")  # Runners In Scoring Positionでの三振数
    ab_at_risp: Optional[int] = Field(None, description="RISPでの打席数")  # Runners In Scoring Positionでの打席数
    avg_at_risp: Optional[float] = Field(None, description="RISPでの打率", ge=0.0, le=1.0)  # Runners In Scoring Positionでの打率
    obp_at_risp: Optional[float] = Field(None, description="RISPでの出塁率", ge=0.0, le=1.0)  # Runners In Scoring Positionでの出塁率
    slg_at_risp: Optional[float] = Field(None, description="RISPでの長打率", ge=0.0, le=5.0)  # Runners In Scoring Positionでの長打率
    ops_at_risp: Optional[float] = Field(None, description="RISPでのOPS", ge=0.0, le=5.0)  # Runners In Scoring PositionでのOPS
    # Bases loaded stats
    hits_at_bases_loaded: Optional[int] = Field(None, description="満塁での安打数")  # 満塁での安打数
    grandslam: Optional[int] = Field(None, description="満塁本塁打数")  # 満塁本塁打数
    doubles_at_bases_loaded: Optional[int] = Field(None, description="満塁での二塁打数")  # 満塁での二塁打数
    triples_at_bases_loaded: Optional[int] = Field(None, description="満塁での三塁打数")  # 満塁での三塁打数
    singles_at_bases_loaded: Optional[int] = Field(None, description="満塁での単打数")
    bb_hbp_at_bases_loaded: Optional[int] = Field(None, description="満塁での四球と死球数")  # 満塁での四球と死球数
    so_at_bases_loaded: Optional[int] = Field(None, description="満塁での三振数")  # 満塁での三振数
    ab_at_bases_loaded: Optional[int] = Field(None, description="満塁での打席数")
    avg_at_bases_loaded: Optional[float] = Field(None, description="満塁での打率", ge=0.0, le=1.0)  # 満塁での打率
    obp_at_bases_loaded: Optional[float] = Field(None, description="満塁での出塁率", ge=0.0, le=1.0)  # 満塁での出塁率
    slg_at_bases_loaded: Optional[float] = Field(None, description="満塁での長打率", ge=0.0, le=5.0)  # 満塁での長打率
    ops_at_bases_loaded: Optional[float] = Field(None, description="満塁でのOPS", ge=0.0, le=5.0)  # 満塁でのOPS
    # Runner on 1st base stats
    hits_at_runner_on_1b: Optional[int] = Field(None, description="1塁走者ありでの安打数")  # 1塁走者ありでの安打数
    homeruns_at_runner_on_1b: Optional[int] = Field(None, description="1塁走者ありでの本塁打数")  # 1塁走者ありでの本塁打数
    doubles_at_runner_on_1b: Optional[int] = Field(None, description="1塁走者ありでの二塁打数")  # 1塁走者ありでの二塁打数
    triples_at_runner_on_1b: Optional[int] = Field(None, description="1塁走者ありでの三塁打数")  # 1塁走者ありでの三塁打数
    singles_at_runner_on_1b: Optional[int] = Field(None, description="1塁走者ありでの単打数")
    bb_hbp_at_runner_on_1b: Optional[int] = Field(None, description="1塁走者ありでの四球と死球数")
    so_at_runner_on_1b: Optional[int] = Field(None, description="1塁走者ありでの三振数")
    ab_at_runner_on_1b: Optional[int] = Field(None, description="1塁走者ありでの打席数")
    avg_at_runner_on_1b: Optional[float] = Field(None, description="1塁走者ありでの打率", ge=0.0, le=1.0)  # 1塁走者ありでの打率
    obp_at_runner_on_1b: Optional[float] = Field(None, description="1塁走者ありでの出塁率", ge=0.0, le=1.0)  # 1塁走者ありでの出塁率
    slg_at_runner_on_1b: Optional[float] = Field(None, description="1塁走者ありでの長打率", ge=0.0, le=5.0)  # 1塁走者ありでの長打率
    ops_at_runner_on_1b: Optional[float] = Field(None, description="1塁走者ありでのOPS", ge=0.0, le=5.0)


# Pydantic model for season pitching stats
class PlayerPitchingSeasonStats(BaseModel):
    """
    選手の年度別投手成績を表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    idfg: int = Field(..., description="選手ID（FanGraphs）")
    season: Optional[int] = Field(None, description="シーズン年")
    name: str = Field(..., description="選手名")
    team: Optional[str] = Field(None, description="所属チーム名")
    league: Optional[str] = Field(None, description="所属リーグ")
    w: Optional[int] = Field(None, description="勝利数")
    l: Optional[int] = Field(None, description="敗北数")
    sv: Optional[int] = Field(None, description="セーブ数")
    g: Optional[int] = Field(None, description="出場試合数")
    gs: Optional[int] = Field(None, description="先発試合数")
    ip: Optional[float] = Field(None, description="投球回数")
    h: Optional[int] = Field(None, description="被安打数")
    hr: Optional[int] = Field(None, description="被本塁打数")
    r: Optional[int] = Field(None, description="自責点")
    er: Optional[int] = Field(None, description="")
    bb: Optional[int] = Field(None, description="与四球数")
    so: int = Field(..., description="三振数")
    hbp: Optional[int] = Field(None, description="被死球数")  # Hit By Pitch
    whip: float = Field(..., description="WHIP", ge=0.0)  # WHIPは0以上の値
    era: float = Field(..., description="防御率", ge=0.0)  # 防御率も0以上の値
    fip: Optional[float] = Field(None, description="FIP", ge=0.0)  # FIPも0以上の値
    k_9: Optional[float] = Field(None, description="9イニングあたりの三振数", ge=0.0)  # 9イニングあたりの三振数も0以上の値
    bb_9: Optional[float] = Field(None, description="9イニングあたりの与四球数", ge=0.0)  # 9イニングあたりの与四球数も0以上の値
    k_bb: Optional[float] = Field(None, description="三振と四球の比率", ge=0.0)  # 三振と四球の比率も0以上の値
    avg: Optional[float] = Field(None, description="被打率", ge=0.0, le=1.0)  # 被打率も0.0から1.0の範囲
    war: Optional[float] = Field(None, description="fWAR")
    wpa: Optional[float] = Field(None, description="wPA")
    swstrpct: Optional[float] = Field(None, description="スイングミス率", ge=0.0, le=1.0)  # スイングミス率も0.0から1.0の範囲
    gbpct: Optional[float] = Field(None, description="ゴロ率", ge=0.0, le=1.0)  # ゴロ率も0.0から1.0の範囲
    lobpct: Optional[float] = Field(None, description="残塁率", ge=0.0, le=1.0)  # 残塁率も0.0から1.0の範囲
    hr_9: Optional[float] = Field(None, description="9イニングあたりの被本塁打数", ge=0.0)  # 9イニングあたりの被本塁打数も0以上の値
    # h_9: Optional[float] = Field(None, description="9イニングあたりの被安打数", ge=0.0)  # 9イニングあたりの被安打数も0以上の値
    barrelpct: Optional[float] = Field(None, description="被バレル%", ge=0.0, le=1.0)  # Barrel Percentageも0.0から1.0の範囲
    hardhitpct: Optional[float] = Field(None, description="被ハードヒット%", ge=0.0, le=1.0)  # Hard Hit Percentageも0.0から1.0の範囲


# Pydantic model for all detailed Statcast data from 2021 to 2025 (to date)
class PlayerStatcastData(BaseModel):
    """
    全ての試合のStatcastデータを表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    pitch_type: Optional[str] = Field(None, description="投球タイプ")
    game_date: datetime = Field(..., description="試合日")
    pitcher_name: str = Field(..., description="投手名")
    batter_id: int = Field(..., description="打者ID（MLB）")
    pitcher_id: int = Field(..., description="投手ID（MLB）")
    batter_name: Optional[str] = Field(None, description="打者名")
    game_year: int = Field(..., description="シーズン年")
    events: Optional[str] = Field(None, description="イベントタイプ")  # イベントタイプはオプション
    game_type: Optional[str] = Field(None, description="試合タイプ")  # 試合タイプはオプション
    hit_location: Optional[int] = Field(None, description="ヒット位置")  # ヒット位置はオプション
    balls: int = Field(..., description="ボール数")
    strikes: int = Field(..., description="ストライク数")
    release_speed: Optional[float] = Field(None, description="投球速度 (mph)")  # 投球速度は0以上の値
    release_pos_x: Optional[float] = Field(None, description="投球リリース位置X座標 (フィート)")  # X座標は-100から100の範囲
    release_pos_z: Optional[float] = Field(None, description="投球リリース位置Z座標 (フィート)")  # Z座標は0から10の範囲
    pfx_x: Optional[float] = Field(None, description="投球のPFX X成分 (フィート)")  # PFX X成分はオプション
    pfx_z: Optional[float] = Field(None, description="投球のPFX Z成分 (フィート)")  # PFX Z成分はオプション
    plate_x: Optional[float] = Field(None, description="プレート位置X座標 (フィート)")  # プレート位置X座標はオプション
    plate_z: Optional[float] = Field(None, description="プレート位置Z座標 (フィート)")  # プレート位置Z座標はオプション
    description: Optional[str] = Field(None, description="投球の説明")  # 投球の説明はオプション
    type: Optional[str] = Field(None, description="投球のタイプ")  # 投球のタイプはオプション
    inning: Optional[int] = Field(None, description="イニング")  # イニングはオプション
    zone: Optional[int] = Field(None, description="ゾーン番号")  # ゾーン番号はオプション
    on_1b: Optional[int] = Field(None, description="Whether there is a runner on 1st base. If so, mlb_id is provided. If not, it is 0.")  # 1塁にランナーがいるかどうか
    on_2b: Optional[int] = Field(None, description="Whether there is a runner on 2nd base. If so, mlb_id is provided. If not, it is 0.")  # 2塁にランナーがいるかどうか
    on_3b: Optional[int] = Field(None, description="Whether there is a runner on 3rd base. If so, mlb_id is provided. If not, it is 0.")  # 3塁にランナーがいるかどうか
    hit_distance_sc: Optional[int] = Field(None, description="ヒットの飛距離 (フィート)")  # ヒットの飛距離はオプション
    launch_speed: Optional[float] = Field(None, description="打球の発射速度 (mph)")  # 打球の発射速度はオプション
    launch_angle: Optional[int] = Field(None, description="打球の発射角度 (度)")
    woba_value: Optional[float] = Field(None, description="wOBA値")  # wOBA値は0.0から1.0の範囲
    launch_speed_angle: Optional[int] = Field(None, description="発射速度と角度の組み合わせ")  # 発射速度と角度の組み合わせはオプション
    pitch_number: int = Field(..., description="投球番号")
    at_bat_number: int = Field(..., description="打席番号")
    game_pk: Optional[str] = Field(None, description="試合PK")  # 試合PKはオプション



# Pydantic model for offensive stats monthly
class PlayerMonethlyOffensiveStats(BaseModel):
    """
    選手の月別打撃成績を表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    game_year: int = Field(..., description="シーズン年")
    game_month: int = Field(..., description="月 (1-12)")
    batter_name: str = Field(..., description="選手名")
    batter_id: int = Field(..., description="選手ID（MLB）")
    hits: int = Field(..., description="安打数")
    home_runs: int = Field(..., description="本塁打数")
    doubles: int = Field(..., description="二塁打数")
    triples: int = Field(..., description="三塁打数")
    singles: int = Field(..., description="単打数")
    walks_and_hbp: int = Field(..., description="四死球数")
    at_bats: int = Field(..., description="打席数")
    batting_average: float = Field(..., description="打率", ge=0.0, le=1.0)  # 打率は0.0から1.0の範囲
    on_base_percentage: float = Field(..., description="出塁率", ge=0.0, le=1.0)  # 出塁率も0.0から1.0の範囲
    slugging_percentage: float = Field(..., description="長打率", ge=0.0, le=4.0)  # 長打率は1.0を超えることがあるため、最大値を調整
    on_base_plus_slugging: float = Field(..., description="OPS", ge=0.0, le=5.0)  # OPSも1.0を超えることがあるため、最大値を調整


# Pydantic model for batter perfomance by strike count
class PlayerBatterPerformanceByStrikeCount(BaseModel):
    """
    選手の打席ごとのストライクカウント別パフォーマンスを表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    game_year: int = Field(..., description="シーズン年")
    batter_name: str = Field(..., description="選手名")
    batter_id: int = Field(..., description="選手ID（MLB）")
    strike_count: int = Field(..., description="ストライクカウント (0-2)")
    total_hits: int = Field(..., description="ヒット数")
    total_at_bats: int = Field(..., description="打席数")
    total_plate_appearances_for_obp: int = Field(..., description="出塁率計算用の打席数")
    batting_average_at_strike_count: float = Field(..., description="ストライクカウントごとの打率", ge=0.0, le=1.0)  # 打率は0.0から1.0の範囲
    on_base_percentage_at_strike_count: float = Field(..., description="ストライクカウントごとの出塁率", ge=0.0, le=1.0)  # 出塁率も0.0から1.0の範囲
    slugging_percentage_at_strike_count: float = Field(..., description="ストライクカウントごとの長打率", ge=0.0, le=4.0)  # 長打率は1.0を超えることがあるため、最大値を調整
    total_bases_for_slugging: int = Field(..., description="長打率計算用の総塁数")
    total_home_runs: int = Field(..., description="本塁打数")
    total_singles: int = Field(..., description="単打数")
    total_doubles: int = Field(..., description="二塁打数")
    total_triples: int = Field(..., description="三塁打数")
    total_extra_base_hits: int = Field(..., description="長打数（単打を除く）")


# Pydantic model for batter performance at risp monthly
class PlayerBatterPerformanceAtRISPMonthly(BaseModel):
    """
    選手の月別RISP (Runners In Scoring Position) パフォーマンスを表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    game_year: int = Field(..., description="シーズン年")
    game_month: int = Field(..., description="月 (1-12)")
    batter_name: str = Field(..., description="選手名")
    batter_id: int = Field(..., description="選手ID（MLB）")
    hits_at_risp: int = Field(..., description="RISPでの安打数")
    home_runs_at_risp: int = Field(..., description="RISPでの本塁打数")
    doubles_at_risp: int = Field(..., description="RISPでの二塁打数")
    triples_at_risp: int = Field(..., description="RISPでの三塁打数")
    singles_at_risp: int = Field(..., description="RISPでの単打数")
    at_bats_at_risp: int = Field(..., description="RISPでの打席数")
    batting_average_at_risp: float = Field(..., description="RISPでの打率", ge=0.0, le=1.0)  # RISPでの打率は0.0から1.0の範囲
    slugging_percentage_at_risp: float = Field(..., description="RISPでの長打率", ge=0.0, le=4.0)  # RISPでの長打率は1.0を超えることがあるため、最大値を調整


# Pydantic model for batter performance rolling vs season stats
class PlayerBatterPerformanceFlags(BaseModel):
    """
    Batter performance flags 'Red Hot', 'Slump', or else based on rolling stats vs season stats for the last 7 days and 15 days
    """
    game_date: datetime = Field(..., description="試合日")
    batter_name: Optional[str] = Field(None, description="選手名")
    batter_id: Optional[int] = Field(None, description="選手ID（MLB）")
    team: Optional[str] = Field(None, description="所属チーム名")
    age: Optional[int] = Field(None, description="選手の年齢")
    hrs_7days: Optional[int] = Field(None, description="Last 7 days home runs")
    abs_per_hr_7days: Optional[float] = Field(None, description="NUmber of at-bats per home run in the last 7 days")
    is_red_hot_hr_7days: Optional[bool] = Field(None, description="Is the batter 'Red Hot' based on home runs in the last 7 days")
    is_slump_hr_7days: Optional[bool] = Field(None, description="Is the batter in a 'Slump' based on home runs in the last 7 days")
    ba_7days: Optional[float] = Field(None, description="Batting average in the last 7 days")
    is_red_hot_ba_7days: Optional[bool] = Field(None, description="Is the batter 'Red Hot' based on batting average in the last 7 days")
    is_slump_ba_7days: Optional[bool] = Field(None, description="Is the batter in a 'Slump' based on batting average in the last 7 days")
    ops_7days: Optional[float] = Field(None, description="OPS in the last 7 days")
    is_red_hot_ops_7days: Optional[bool] = Field(None, description="Is the batter 'Red Hot' based on OPS in the last 7 days")
    is_slump_ops_7days: Optional[bool] = Field(None, description="Is the batter in a 'Slump' based on OPS in the last 7 days")
    barrels_percentage_7days: Optional[float] = Field(None, description="Barrel percentage in the last 7 days")
    is_red_hot_barrels_7days: Optional[bool] = Field(None, description="Is the batter 'Red Hot' based on barrel percentage in the last 7 days")
    is_slump_barrels_7days: Optional[bool] = Field(None, description="Is the batter in a 'Slump' based on barrel percentage in the last 7 days")
    hard_hit_percentage_7days: Optional[float] = Field(None, description="Hard hit percentage in the last 7 days")
    is_red_hot_hard_hit_7days: Optional[bool] = Field(None, description="Is the batter 'Red Hot' based on hard hit percentage in the last 7 days")
    is_slump_hard_hit_7days: Optional[bool] = Field(None, description="Is the batter in a 'Slump' based on hard hit percentage in the last 7 days")
    hrs_15days: Optional[int] = Field(None, description="Last 15 days home runs")
    abs_per_hr_15days: Optional[float] = Field(None, description="Number of at-bats per home run in the last 15 days")
    is_red_hot_hr_15days: Optional[bool] = Field(None, description="Is the batter 'Red Hot' based on home runs in the last 15 days")
    is_slump_hr_15days: Optional[bool] = Field(None, description="Is the batter in a 'Slump' based on home runs in the last 15 days")
    ba_15days: Optional[float] = Field(None, description="Batting average in the last 15 days")
    is_red_hot_ba_15days: Optional[bool] = Field(None, description="Is the batter 'Red Hot' based on batting average in the last 15 days")
    is_slump_ba_15days: Optional[bool] = Field(None, description="Is the batter in a 'Slump' based on batting average in the last 15 days")
    ops_15days: Optional[float] = Field(None, description="OPS in the last 15 days")
    is_red_hot_ops_15days: Optional[bool] = Field(None, description="Is the batter 'Red Hot' based on OPS in the last 15 days")
    is_slump_ops_15days: Optional[bool] = Field(None, description="Is the batter in a 'Slump' based on OPS in the last 15 days")
    barrels_percentage_15days: Optional[float] = Field(None, description="Barrel percentage in the last 15 days")
    is_red_hot_barrels_15days: Optional[bool] = Field(None, description="Is the batter 'Red Hot' based on barrel percentage in the last 15 days")
    is_slump_barrels_15days: Optional[bool] = Field(None, description="Is the batter in a 'Slump' based on barrel percentage in the last 15 days")
    hard_hit_percentage_15days: Optional[float] = Field(None, description="Hard hit percentage in the last 15 days")
    is_red_hot_hard_hit_15days: Optional[bool] = Field(None, description="Is the batter 'Red Hot' based on hard hit percentage in the last 15 days")
    is_slump_hard_hit_15days: Optional[bool] = Field(None, description="Is the batter in a 'Slump' based on hard hit percentage in the last 15 days")



# Pydantic model for pitcher performance by inning
class PlayerPitcherPerformanceByInning(BaseModel):
    """
    選手のイニングごとの投手パフォーマンスを表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    game_year: int = Field(..., description="シーズン年")
    pitcher_name: str = Field(..., description="選手名")
    pitcher_id: int = Field(..., description="選手ID（MLB）")
    inning: int = Field(..., description="イニング (1-9)")
    hits_allowed: int = Field(..., description="被安打数")
    outs_recorded: int = Field(..., description="アウト数")
    batting_average_against: float = Field(..., description="被打率", ge=0.0, le=1.0)  # 被打率は0.0から1.0の範囲
    obp_numerator: int = Field(..., description="出塁率計算用の分子")
    obp_denominator: int = Field(..., description="出塁率計算用の分母")
    slg_numerator: int = Field(..., description="長打率計算用の分子")
    slg_denominator: int = Field(..., description="長打率計算用の分母")
    ops_against: float = Field(..., description="OPS (On-base Plus Slugging) against", ge=0.0, le=5.0)  # OPSは1.0を超えることがあるため、最大値を調整
    home_runs_allowed: int = Field(..., description="被本塁打数")
    non_home_run_hits_allowed: int = Field(..., description="本塁打以外の被安打数")
    free_passes: int = Field(..., description="与四死球数")  # 与四死球数は、四球と死球の合計


# Pydantic model for team batting stats leaderboard
class TeamBattingStatsLeaderboard(BaseModel):
    """
    チームの打撃成績リーダーボードを表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    season: int = Field(..., description="シーズン年")
    team: str = Field(..., description="チーム名")
    league: str = Field(..., description="リーグ名")
    hr: int = Field(..., description="本塁打数")
    h: int = Field(..., description="安打数")
    rbi: int = Field(..., description="打点数")
    r: int = Field(..., description="得点数")
    bb: int = Field(..., description="四球数")
    so: int = Field(..., description="三振数")
    sb: int = Field(..., description="盗塁数")
    avg: float = Field(..., description="打率", ge=0.0, le=1.0)
    obp: float = Field(..., description="出塁率", ge=0.0, le=1.0)
    slg: float = Field(..., description="長打率", ge=0.0, le=5.0)
    ops: float = Field(..., description="OPS (On-base Plus Slugging)", ge=0.0, le=5.0)
    war: Optional[float] = Field(None, description="fWAR")
    wrcplus: Optional[int] = Field(None, description="wRC+")
    barrelpct: Optional[float] = Field(None, description="Barrel Percentage", ge=0.0, le=1.0)  # Barrel Percentageも0.0から1.0の範囲
    hardhitpct: Optional[float] = Field(None, description="Hard Hit Percentage", ge=0.0, le=1.0)  # Hard Hit Percentageも0.0から1.0の範囲
    woba: Optional[float] = Field(None, description="wOBA")

# Pydantic model for team pitching stats leaderboard
class TeamPitchingStatsLeaderboard(BaseModel):
    """
    チームの投手成績リーダーボードを表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    season: int = Field(..., description="シーズン年")
    team: str = Field(..., description="チーム名")
    league: str = Field(..., description="リーグ名")
    era: float = Field(..., description="防御率", ge=0.0)  # 防御率は0以上の値
    w: int = Field(..., description="勝利数")
    l: int = Field(..., description="敗北数")
    so: int = Field(..., description="三振数")
    h: int = Field(..., description="被安打数")
    r: int = Field(..., description="失点数")
    er: int = Field(..., description="自責点数")
    bb: int = Field(..., description="与四球数")
    fip: Optional[float] = Field(None, description="FIP (Fielding Independent Pitching)", ge=0.0)  # FIPも0以上の値
    war: Optional[float] = Field(None, description="fWAR")
    whip: Optional[float] = Field(None, description="WHIP (Walks and Hits per Inning Pitched)", ge=0.0)
    k_9: Optional[float] = Field(None, description="9イニングあたりの三振数", ge=0.0)  # 9イニングあたりの三振数も0以上の値
    bb_9: Optional[float] = Field(None, description="9イニングあたりの与四球数", ge=0.0)  # 9イニングあたりの与四球数も0以上の値
    k_bb: Optional[float] = Field(None, description="三振と四球の比率", ge=0.0)
    hr_9: Optional[float] = Field(None, description="9イニングあたりの被本塁打数", ge=0.0)  # 9イニングあたりの被本塁打数も0以上の値
    # h_9: Optional[float] = Field(None, description="9イニングあたりの被安打数", ge=0.0)  # 9イニングあたりの被安打数も0以上の値
    avg: Optional[float] = Field(None, description="被打率", ge=0.0, le=1.0)  # 被打率も0.0から1.0の範囲
    hr: Optional[int] = Field(None, description="被本塁打数")
    lobpct: Optional[float] = Field(None, description="被残塁率", ge=0.0, le=1.0)  # 残塁率も0.0から1.0の範囲


# Pydantic model for batter split stats by inning
class PlayerBattingStatsByInning(BaseModel):
    """
    選手のイニングごとの打撃成績を表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    game_year: int = Field(..., description="シーズン年")
    batter_name: str = Field(..., description="選手名")
    batter_id: int = Field(..., description="選手ID（MLB）")
    inning: int = Field(..., description="イニング (1-9)")
    hits_by_inning: Optional[int] = Field(None, description="イニングごとの安打数")
    homeruns_by_inning: Optional[int] = Field(None, description="イニングごとの本塁打数")
    doubles_by_inning: Optional[int] = Field(None, description="イニングごとの二塁打数")
    triples_by_inning: Optional[int] = Field(None, description="イニングごとの三塁打数")
    singles_by_inning: Optional[int] = Field(None, description="イニングごとの単打数")
    bb_hbp_by_inning: Optional[int] = Field(None, description="イニングごとの四死球数")
    so_by_inning: Optional[int] = Field(None, description="イニングごとの三振数")
    ab_by_inning: Optional[int] = Field(None, description="イニングごとの打席数")
    avg_by_inning: Optional[float] = Field(None, description="イニングごとの打率", ge=0.0, le=1.0)  # イニングごとの打率
    obp_by_inning: Optional[float] = Field(None, description="イニングごとの出塁率", ge=0.0, le=1.0)  # イニングごとの出塁率
    slg_by_inning: Optional[float] = Field(None, description="イニングごとの長打率", ge=0.0, le=5.0)  # イニングごとの長打率
    ops_by_inning: Optional[float] = Field(None, description="イニングごとのOPS", ge=0.0, le=5.0)  # イニングごとのOPS
    hitting_events_by_inning: Optional[int] = Field(None, description="イニングごとのヒッティングイベント数")  # イニングごとのヒッティングイベント数
    launch_angle_by_inning: Optional[float] = Field(None, description="イニングごとの打球の発射角度 (度)")  # イニングごとの打球の発射角度 (度)
    exit_velocity_by_inning: Optional[float] = Field(None, description="イニングごとの打球の発射速度 (mph)")  # イニングごとの打球の発射速度 (mph)
    bat_speed_by_inning: Optional[float] = Field(None, description="イニングごとのバットスピード (mph)")  # イニングごとのバットスピード (mph)
    swing_length_by_inning: Optional[float] = Field(None, description="イニングごとのスイング長 (フィート)")  # イニングごとのスイング長 (フィート)
    hard_hit_count_by_inning: Optional[int] = Field(None, description="イニングごとのハードヒット数")  # イニングごとのハードヒット数
    denominator_for_hard_hit_rate_by_inning: Optional[int] = Field(None, description="イニングごとのハードヒット率計算用の分母")  # イニングごとのハードヒット率計算用の分母
    hard_hit_rate_by_inning: Optional[float] = Field(None, description="イニングごとのハードヒット率", ge=0.0, le=1.0)  # イニングごとのハードヒット率
    barrels_count_by_inning: Optional[int] = Field(None, description="イニングごとのバレル数")  # イニングごとのバレル数
    total_batted_balls_by_inning: Optional[int] = Field(None, description="イニングごとの打球数")  # イニングごとの打球数
    barrels_rate_by_inning: Optional[float] = Field(None, description="イニングごとのバレル率", ge=0.0, le=1.0)  # イニングごとのバレル率
    strike_rate_by_inning: Optional[float] = Field(None, description="イニングごとのストライク率", ge=0.0, le=1.0)  # イニングごとのストライク率
    swinging_strike_count_by_inning: Optional[int] = Field(None, description="イニングごとのスイングミス数")  # イニングごとのスイングミス数
    swinging_strike_rate_by_inning: Optional[float] = Field(None, description="イニングごとのスイングミス率", ge=0.0, le=1.0)  # イニングごとのスイングミス率



# 選手の詳細情報と全シーズン成績を表すPydanticモデル
class PlayerDetailsResponse(BaseModel):
    """
    選手の詳細情報と全シーズン成績を表すスキーマ。
    APIエンドポイントのレスポンスモデルとして使用されます。
    """
    player_info: PlayerBasicInfo = Field(..., description="選手の基本情報")
    batting_season_stats: Optional[List[PlayerBattingSeasonStats]] = Field([], description="選手の年度別打撃成績のリスト")
    pitching_season_stats: Optional[List[PlayerPitchingSeasonStats]] = Field([], description="選手の年度別投手成績のリスト")
    batter_split_stats: Optional[List[PlayerBattingSplitStats]] = Field([], description="選手の打撃スプリット成績のリスト")
    batter_career_stats: Optional[List[PlayerBattingSeasonStats]] = Field(None, description="選手のキャリア打撃成績")
    pitcher_career_stats: Optional[List[PlayerPitchingSeasonStats]] = Field(None, description="選手のキャリア投手成績")


# 選手名を検索した結果のリストを表すPydanticモデル
class PlayerSearchItem(BaseModel):
    """
    選手名検索結果の各項目を表すスキーマ。
    """
    # 検索結果には、検索に使ったID (idfg) と、mlb_idの両方を含める
    idfg: Optional[int] = Field(None, description="FanGraphs選手ID")
    mlb_id: Optional[int] = Field(None, description="MLB選手ID")
    player_name: str = Field(..., description="選手名") # full_nameがここに入る


class PlayerSearchResults(BaseModel):
    """
    選手名検索の全体結果を表すスキーマ。
    """
    query: Optional[str] = Field("", description="検索クエリ")
    results: List[PlayerSearchItem] = Field([], description="検索に一致した選手のリスト")


# ★★★ 修正箇所: ランキング結果用のPydanticモデルを追加 ★★★
class PlayerRankingResult(BaseModel):
    # ランキングの指標名とその順位を動的に保持するため、Extra を許可する
    # Pydantic v2では extra='allow' を使う
    model_config = {'extra': 'allow'} # Pydantic v2の場合
    # または pydantic v1 の場合: class Config: extra = 'allow'

    # 例: 必須フィールドがないため、空のモデルとして定義し、extraで動的なキーを許可
    # もし特定のランキングが常に含まれるならここに定義
    # ops: Optional[int] = None
    # hr: Optional[int] = None


# ★★★ 変更点: 新しいQ&Aリクエストモデルの追加 ★★★
class QnARequest(BaseModel):
    query: str
    season: Optional[int] = None
