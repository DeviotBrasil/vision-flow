import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QResizeEvent, QShowEvent
from PySide6.QtWidgets import QApplication, QMainWindow

from visionflow.branding import APP_DISPLAY_NAME
from visionflow.domain.contracts.camera import CameraPort
from visionflow.domain.contracts.thumbnail_cache import ThumbnailReader
from visionflow.domain.use_cases.camera_config import CameraConfigService
from visionflow.domain.use_cases.captures import CaptureService
from visionflow.domain.use_cases.logs import LogService
from visionflow.domain.use_cases.recordings import RecordingService
from visionflow.domain.use_cases.yolo_dataset import YoloDatasetService
from visionflow.infrastructure.camera.factory import (
    backend_available,
    create_camera,
)
from visionflow.infrastructure.camera.native import (
    SYNC_COMMAND,
    ensure_native_lib_path,
    is_bundled_sdk_available,
    resolve_opt_lib_dir,
)
from visionflow.infrastructure.camera.opt import sdk_available
from visionflow.infrastructure.logging_config import (
    attach_db_log_handler,
    configure_logging,
)
from visionflow.infrastructure.paths import (
    CAPTURES_DIR,
    RECORDINGS_DIR,
    THUMBS_DIR,
    ensure_data_dirs,
)
from visionflow.infrastructure.persistence import (
    SqliteCameraConfigRepository,
    SqliteCaptureRepository,
    SqliteLogRepository,
    SqliteRecordingRepository,
    SqliteYoloRepository,
    initialize,
)
from visionflow.infrastructure.storage.cv_image_file_importer import (
    CvImageFileImporter,
)
from visionflow.infrastructure.thumbnails.disk_cache import DiskThumbnailCache
from visionflow.infrastructure.video.opencv_video_recorder import (
    OpenCvVideoRecorder,
)
from visionflow.presentation.camera_controller import (
    CameraController,
    CameraWorkerFactories,
)
from visionflow.presentation.layouts.default_layout import DefaultLayout
from visionflow.presentation.media_thumbnail_loader import MediaThumbnailLoader
from visionflow.presentation.paths import ICONS_DIR
from visionflow.presentation.qt_image_storage import QtImageStorage
from visionflow.presentation.qt_logging import install_qt_message_handler
from visionflow.presentation.screens.factory import (
    DataDirs,
    ScreenServices,
    build_screen_factories,
)
from visionflow.presentation.themes.theme_manager import ThemeManager
from visionflow.presentation.window_constraints import WINDOW_MINIMUM_SIZE
from visionflow.version import app_version

_logger = logging.getLogger(__name__)


@dataclass
class AppDependencies:
    """Dependências montadas na raiz de composição e injetadas na UI."""

    capture_service: CaptureService
    recording_service: RecordingService
    config_service: CameraConfigService
    log_service: LogService
    yolo_service: YoloDatasetService
    thumbnail_reader: ThumbnailReader
    sdk_available: Callable[[], bool]
    backend_available: Callable[[str], bool]
    camera_factory: Callable[[str], CameraPort]


def build_dependencies(
    log_repository: SqliteLogRepository | None = None,
) -> AppDependencies:
    """Monta o grafo de dependências (persistência, câmera e serviços)."""
    initialize()
    capture_repository = SqliteCaptureRepository()
    config_repository = SqliteCameraConfigRepository()
    yolo_repository = SqliteYoloRepository()
    log_repo = log_repository or SqliteLogRepository()
    image_storage = QtImageStorage(CAPTURES_DIR)
    file_importer = CvImageFileImporter(CAPTURES_DIR)
    recording_repository = SqliteRecordingRepository(RECORDINGS_DIR)
    thumbnail_cache = DiskThumbnailCache(THUMBS_DIR)
    thumbnail_reader = thumbnail_cache.as_reader()
    log_service = LogService(log_repo)
    log_service.prune_old_logs()
    return AppDependencies(
        capture_service=CaptureService(
            capture_repository,
            image_storage,
            file_importer,
            thumbnail_cache=thumbnail_cache,
        ),
        recording_service=RecordingService(
            recording_repository,
            thumbnail_cache=thumbnail_cache,
        ),
        config_service=CameraConfigService(config_repository),
        log_service=log_service,
        yolo_service=YoloDatasetService(yolo_repository),
        thumbnail_reader=thumbnail_reader,
        sdk_available=sdk_available,
        backend_available=backend_available,
        camera_factory=create_camera,
    )


class MainApplication(QMainWindow):
    """Janela principal do Vision Flow.

    Monta o layout padrão, inicializa o gerenciador de temas e aplica a
    preferência salva do usuário na abertura da aplicação.
    """

    def __init__(self, deps: AppDependencies):
        """Inicializa a janela, monta a UI e restaura o tema salvo."""
        super().__init__()

        self.setWindowTitle(f"{APP_DISPLAY_NAME} v{app_version()}")
        self.setWindowIcon(QIcon(str(ICONS_DIR / "icon_app.svg")))
        self._window_min = WINDOW_MINIMUM_SIZE
        self._clamping_resize = False

        self.theme_manager = ThemeManager(QApplication.instance())
        self._thumbnail_loader = MediaThumbnailLoader(deps.thumbnail_reader, self)

        # Controlador único de câmera, com a câmera e os serviços injetados.
        controller = CameraController(
            CameraWorkerFactories(deps.camera_factory, OpenCvVideoRecorder),
            deps.config_service,
            deps.sdk_available,
            deps.backend_available,
            parent=self,
        )

        # SETUP LAYOUT
        self.ui = DefaultLayout()
        self.ui.setup_ui(
            self,
            self.theme_manager,
            controller,
            build_screen_factories(
                controller,
                ScreenServices(
                    captures=deps.capture_service,
                    recordings=deps.recording_service,
                    config=deps.config_service,
                    logs=deps.log_service,
                    yolo=deps.yolo_service,
                ),
                DataDirs(
                    captures=CAPTURES_DIR,
                    recordings=RECORDINGS_DIR,
                ),
                thumbnail_loader=self._thumbnail_loader,
            ),
        )

        # Aplica o tema salvo; o sinal theme_changed atualiza a UI.
        self.theme_manager.apply_saved_theme()
        self._apply_window_minimum()

    def _apply_window_minimum(self) -> None:
        """Reaplica o tamanho mínimo na janela e no widget central."""
        self.setMinimumSize(self._window_min)
        central = self.centralWidget()
        if central is not None:
            central.setMinimumSize(self._window_min)

    def minimumSizeHint(self) -> QSize:
        return self._window_min

    def resizeEvent(self, event: QResizeEvent) -> None:
        # Em alguns ambientes o WM ignora setMinimumSize; corrigimos aqui.
        if self._clamping_resize:
            super().resizeEvent(event)
            return

        size = event.size()
        min_w = self._window_min.width()
        min_h = self._window_min.height()
        if size.width() < min_w or size.height() < min_h:
            self._clamping_resize = True
            self.resize(
                max(size.width(), min_w),
                max(size.height(), min_h),
            )
            self._clamping_resize = False
            return

        super().resizeEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        self._apply_window_minimum()
        super().showEvent(event)

    def closeEvent(self, event):
        """Encerra recursos das telas e da câmera antes de fechar a janela."""
        _logger.info("Encerrando aplicação.")
        self._thumbnail_loader.shutdown()
        shutdown_screens = getattr(self.ui, "shutdown_screens", None)
        if callable(shutdown_screens):
            shutdown_screens()
        controller = getattr(self.ui, "camera_controller", None)
        if controller is not None:
            controller.shutdown()
        super().closeEvent(event)


def main() -> int:
    """Cria a aplicação Qt, exibe a janela principal e inicia o loop de eventos.

    Returns:
        Código de saída do ``QApplication.exec()``.
    """
    ensure_native_lib_path()
    ensure_data_dirs()
    initialize()
    log_repository = SqliteLogRepository()
    attach_db_log_handler(log_repository)
    configure_logging()
    if is_bundled_sdk_available():
        _logger.info("SDK OPT embutido no projeto disponível.")
    elif resolve_opt_lib_dir() is not None:
        _logger.info("SDK OPT carregado do runtime instalado no sistema.")
    else:
        _logger.warning(
            "SDK OPT indisponível; fluxo OPT desabilitado até sincronizar o runtime. "
            "Execute: %s",
            SYNC_COMMAND,
        )
    _logger.info("Iniciando %s.", APP_DISPLAY_NAME)
    install_qt_message_handler()

    QApplication.setAttribute(
        Qt.ApplicationAttribute.AA_UseStyleSheetPropagationInWidgetStyles, True
    )
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICONS_DIR / "icon_app.svg")))
    # Fusion + QSS: border-radius consistente entre temas/plataformas.
    app.setStyle("Fusion")
    # A referência precisa ser mantida; sem ela a janela é coletada pelo
    # garbage collector e o app encerra imediatamente.
    window = MainApplication(build_dependencies(log_repository))
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
