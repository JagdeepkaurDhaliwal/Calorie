import io
from app.models import ModelVersion
from app.services.admin_service import try_activate


def test_tc12_upload_invalid_csv(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    bad_csv = b"Invalid,Columns,Only\n1,2,3\n"
    files = {"file": ("bad.csv", io.BytesIO(bad_csv), "text/csv")}

    resp = client.post("/admin/upload-data", files=files, headers=headers)
    assert resp.status_code == 400
    data = resp.json()
    assert "Missing columns" in data["error"]["message"]


def test_upload_valid_csv(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    valid_csv = (
        b"Gender,Age,Height,Weight,Duration,Heart_Rate,Body_Temp,Calories\n"
        b"male,30,175.0,75.0,20.0,110.0,38.0,120.0\n"
        b"female,25,165.0,60.0,25.0,120.0,38.5,140.0\n"
    )
    files = {"file": ("valid.csv", io.BytesIO(valid_csv), "text/csv")}

    resp = client.post("/admin/upload-data", files=files, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["rows"] == 2
    assert data["status"] == "valid"
    assert "dataset_id" in data


def test_models_list_and_activation(client, db_session, admin_token):
    # Ensure a model version exists in this isolated in-memory test database
    version = ModelVersion(
        algorithm="MLPRegressor",
        artifact_dir="ml/artifacts/v1",
        mae=1.215,
        rmse=1.558,
        r2=0.998,
        clf_accuracy=0.894,
        clf_f1=0.895,
        is_active=False,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/admin/models", headers=headers)
    assert resp.status_code == 200
    models = resp.json()
    assert isinstance(models, list)
    assert len(models) >= 1

    # Try activating model
    v_id = models[0]["id"]
    act_resp = client.post(f"/admin/models/{v_id}/activate", headers=headers)
    assert act_resp.status_code == 200
    assert act_resp.json()["is_active"] is True


def test_tc13_and_tc14_retrain_activation_logic(db_session):
    # Test try_activate unit logic
    # Create active model with RMSE 2.0
    active = ModelVersion(
        algorithm="RandomForest",
        artifact_dir="ml/artifacts/v1",
        mae=1.5,
        rmse=2.0,
        r2=0.98,
        clf_accuracy=0.90,
        clf_f1=0.90,
        is_active=True,
    )
    db_session.add(active)
    db_session.commit()
    db_session.refresh(active)

    # TC-14: Candidate with worse RMSE 2.5 must NOT be activated
    worse = ModelVersion(
        algorithm="LinearRegression",
        artifact_dir="ml/artifacts/v1",
        mae=2.0,
        rmse=2.5,
        r2=0.95,
        clf_accuracy=0.88,
        clf_f1=0.88,
        is_active=False,
    )
    db_session.add(worse)
    db_session.commit()
    db_session.refresh(worse)

    ok_worse = try_activate(db_session, worse, force=False)
    assert ok_worse is False
    assert worse.is_active is False
    assert active.is_active is True

    # TC-13: Candidate with better RMSE 1.5 MUST be activated
    better = ModelVersion(
        algorithm="MLPRegressor",
        artifact_dir="ml/artifacts/v1",
        mae=1.1,
        rmse=1.5,
        r2=0.99,
        clf_accuracy=0.92,
        clf_f1=0.92,
        is_active=False,
    )
    db_session.add(better)
    db_session.commit()
    db_session.refresh(better)

    ok_better = try_activate(db_session, better, force=False)
    assert ok_better is True
    assert better.is_active is True
    assert active.is_active is False
