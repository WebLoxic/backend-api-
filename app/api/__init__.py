# app/api/__init__.py

from fastapi import APIRouter
import pkgutil
import importlib
import logging

log = logging.getLogger("app.api")

# Main API router (this is what main.py will include)
router = APIRouter()


def auto_register_routes():
    """
    Auto-discover and register all *_routes.py files inside app/api
    """
    log.info("🔍 Auto-discovering API routes...")

    # __path__ is required for pkgutil to scan this package
    for _, module_name, is_pkg in pkgutil.iter_modules(__path__):
        # only load *_routes.py modules
        if is_pkg or not module_name.endswith("_routes"):
            continue

        try:
            # import module like app.api.orders_routes
            module = importlib.import_module(f"{__name__}.{module_name}")

            # check router exists
            if hasattr(module, "router"):
                router.include_router(module.router)
                log.info("✅ Loaded API router: %s", module_name)
            else:
                log.warning("⚠️ %s has no `router` attribute", module_name)

        except Exception as e:
            log.exception("❌ Failed to load router %s", module_name)


# 🔥 IMPORTANT: auto-register on import
auto_register_routes()
