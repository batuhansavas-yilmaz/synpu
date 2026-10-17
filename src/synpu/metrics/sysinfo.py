import platform
from functools import lru_cache

EDITION_NAMES = {
    "Core": "Home",
    "CoreN": "Home N",
    "CoreSingleLanguage": "Home Single Language",
    "CoreCountrySpecific": "Home China",
    "Professional": "Pro",
    "ProfessionalN": "Pro N",
    "ProfessionalEducation": "Pro Education",
    "ProfessionalEducationN": "Pro Education N",
    "ProfessionalWorkstation": "Pro for Workstations",
    "ProfessionalWorkstationN": "Pro for Workstations N",
    "Enterprise": "Enterprise",
    "EnterpriseN": "Enterprise N",
    "EnterpriseS": "Enterprise LTSC",
    "EnterpriseSN": "Enterprise LTSC N",
    "IoTEnterprise": "IoT Enterprise",
    "Education": "Education",
    "EducationN": "Education N",
}


def format_os_name(system: str | None, release: str | None,
                   version: str | None, edition: str | None) -> str | None:
    if system != "Windows":
        return None
    release = release or ""
    if release == "10":
        try:
            if int(str(version or "").split(".")[-1]) >= 22000:
                release = "11"
        except ValueError:
            pass
    edition_name = EDITION_NAMES.get(edition or "", edition or "")
    parts = ["Windows", release, edition_name]
    return " ".join(part for part in parts if part) or None


@lru_cache(maxsize=1)
def os_name() -> str | None:
    if platform.system() != "Windows":
        return None
    try:
        edition = platform.win32_edition()
    except Exception:
        edition = ""
    return format_os_name("Windows", platform.release(), platform.version(), edition)
