from restpy.auth import (
    RestPyAuthBasic,
    RestPyAuthDisabled,
    RestPyAuthModule,
    RestPyAuthOAuth2,
    RestPyAuthRawToken,
)
from restpy.choices import DataTypeChoice, RequestMethodChoice
from restpy.classes import (
    RESTpyField,
    RESTpyResponse,
    RestPy,
    RestPyFieldWhereData,
    RestPyModule,
    RestPySingleton,
    RestPyURL,
)
from restpy.exceptions import (
    RESTpyTimeOutException,
    RestPyAuthException,
    RestPyException,
    RestPyForbiddenException,
    RestPyInternalServerErrorException,
    RestPyIsClientErrorResponse,
    RestPyIsInformationalResponse,
    RestPyIsRedirectResponse,
    RestPyIsServerErrorResponse,
    RestPyIsSuccessResponse,
    RestPyIsValidStatusResponse,
    RestPyLoginException,
    RestPyMethodNotAllowedException,
    RestPyRequestMethodException,
    RestPyResponseTypeException,
    RestPyRunnerException,
    RestPyStatusCodeException,
    RestPyURLNotFoundException,
    RestPyValidatorException,
)
from restpy.utils import SingletonClass, SingletonMeta, classproperty
from restpy.validators import (
    BaseValidator,
    ChoiceValidator,
    DatetimeObjectValidator,
    DatetimeValidator,
    DateYearMonthDayValidator,
    DateYearMonthValidator,
    IgnoreCaseValidator,
    NumberValidator,
    RequiredFieldValidator,
    StrValidator,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    # [Client]
    "RestPy",
    "RestPySingleton",
    "RestPyModule",
    "RESTpyResponse",
    "RestPyURL",
    "RESTpyField",
    "RestPyFieldWhereData",
    # [Auth]
    "RestPyAuthModule",
    "RestPyAuthBasic",
    "RestPyAuthDisabled",
    "RestPyAuthOAuth2",
    "RestPyAuthRawToken",
    # [Choices]
    "DataTypeChoice",
    "RequestMethodChoice",
    # [Exceptions] building blocks for custom runners and error handling
    "RestPyException",
    "RestPyRunnerException",
    "RestPyStatusCodeException",
    "RestPyAuthException",
    "RestPyLoginException",
    "RestPyRequestMethodException",
    "RestPyResponseTypeException",
    "RestPyURLNotFoundException",
    "RestPyValidatorException",
    "RestPyIsValidStatusResponse",
    "RestPyIsInformationalResponse",
    "RestPyIsSuccessResponse",
    "RestPyIsRedirectResponse",
    "RestPyIsClientErrorResponse",
    "RestPyIsServerErrorResponse",
    "RestPyForbiddenException",
    "RestPyMethodNotAllowedException",
    "RESTpyTimeOutException",
    "RestPyInternalServerErrorException",
    # [Validators]
    "BaseValidator",
    "ChoiceValidator",
    "DatetimeValidator",
    "IgnoreCaseValidator",
    "DatetimeObjectValidator",
    "DateYearMonthDayValidator",
    "DateYearMonthValidator",
    "NumberValidator",
    "RequiredFieldValidator",
    "StrValidator",
    # [Utils]
    "classproperty",
    "SingletonClass",
    "SingletonMeta",
]
