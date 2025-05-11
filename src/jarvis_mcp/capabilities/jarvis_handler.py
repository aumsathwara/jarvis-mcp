from fastapi import HTTPException
from jarvis_cd.basic.pkg import Pipeline

async def create_pipeline(pipeline_id: str) -> dict:
    try:
        Pipeline().create(pipeline_id).build_env().save()
        return {"pipeline_id": pipeline_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create failed: {e}")

async def load_pipeline(pipeline_id: str = None) -> dict:
    try:
        pipeline = Pipeline().load(pipeline_id)
        return {"pipeline_id": pipeline.pipeline_id, "status": "loaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Load failed: {e}")

async def append_pkg(
    pipeline_id: str,
    pkg_type: str,
    pkg_id: str = None,
    do_configure: bool = True,
    **kwargs
) -> dict:
    try:
        # Avoid duplicate do_configure in kwargs
        raw_kwargs = dict(kwargs)
        config_flag = do_configure
        if 'do_configure' in raw_kwargs:
            config_flag = raw_kwargs.pop('do_configure')

        pipeline = Pipeline().load(pipeline_id)
        pipeline.append(
            pkg_type,
            pkg_id=pkg_id,
            do_configure=config_flag,
            **raw_kwargs
        ).save()
        return {"pipeline_id": pipeline_id, "appended": pkg_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Append failed: {e}")

async def configure_pkg(pipeline_id: str, pkg_id: str, **kwargs) -> dict:
    try:
        pipeline = Pipeline().load(pipeline_id)
        pkg = pipeline.get_pkg(pkg_id)
        pkg.configure(**kwargs).save()
        return {"pipeline_id": pipeline_id, "configured": pkg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configure failed: {e}")

async def unlink_pkg(pipeline_id: str, pkg_id: str) -> dict:
    try:
        Pipeline().load(pipeline_id).unlink(pkg_id).save()
        return {"pipeline_id": pipeline_id, "unlinked": pkg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unlink failed: {e}")

async def remove_pkg(pipeline_id: str, pkg_id: str) -> dict:
    try:
        Pipeline().load(pipeline_id).remove(pkg_id).save()
        return {"pipeline_id": pipeline_id, "removed": pkg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remove failed: {e}")

async def run_pipeline(pipeline_id: str) -> dict:
    try:
        Pipeline().load(pipeline_id).run()
        return {"pipeline_id": pipeline_id, "status": "running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Run failed: {e}")

async def destroy_pipeline(pipeline_id: str) -> dict:
    try:
        Pipeline().load(pipeline_id).destroy()
        return {"pipeline_id": pipeline_id, "status": "destroyed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Destroy failed: {e}")
