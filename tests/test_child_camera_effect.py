import pytest

from app.errors import ServiceError
from app.services import accident_service
from app.services.data_files import CHILD_CAMERA_FILE

HEADER = "구분,기간,어린이_보행사고,전체_보행사고,어린이_보행부상자,전체_보행부상자,설치대수,출처\n"


def test_reduction_is_rounded(write_csv):
    data_dir = write_csv(CHILD_CAMERA_FILE, HEADER + "설치 전,2018~2019,3,0,4,0,10,x\n설치 후,2021~2022,1,0,1,0,10,x")
    result = accident_service.child_camera_effect(data_dir)
    assert result.accidents_reduction_percent == 67  # 66.7
    assert (result.before.period, result.after.accidents, result.cameras) == ("2018~2019", 1, 10)


def test_missing_row_is_error(write_csv):
    data_dir = write_csv(CHILD_CAMERA_FILE, HEADER + "설치 전,2018~2019,3,0,4,0,10,x")
    with pytest.raises(ServiceError, match="설치 후"):
        accident_service.child_camera_effect(data_dir)


def test_real_data_matches_press_release(real_data_dir):
    result = accident_service.child_camera_effect(real_data_dir)
    assert (result.before.accidents, result.after.accidents) == (31, 9)
    assert (result.before.injuries, result.after.injuries) == (33, 9)
    assert (result.before.period, result.after.period) == ("2018~2019", "2021~2022")
    assert result.accidents_reduction_percent == 71 and result.cameras == 107
