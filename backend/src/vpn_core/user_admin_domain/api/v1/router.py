from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from vpn_core.common.auth.bot_api_key import verify_admin_telegram_id, verify_bot_api_key
from vpn_core.user_admin_domain.api.v1.dependency import UserAdminServiceDep
from vpn_core.user_admin_domain.api.v1.dto import (
    AddCollaboratorDiscountDTO,
    AdminUserConfigDetailDTO,
    AdminUserConfigItemDTO,
    AdminUserConfigListResponseDTO,
    AdminUserDetailDTO,
    AdminUserListItemDTO,
    BlockUserDTO,
    CollaboratorDiscountRuleDTO,
    PaginatedUsersResponseDTO,
)
from vpn_core.user_admin_domain.service import USER_PAGE_SIZE_DEFAULT

router = APIRouter(
    prefix="/api/v1/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(verify_bot_api_key), Depends(verify_admin_telegram_id)],
)


def _user_list_item_dto(item) -> AdminUserListItemDTO:
    return AdminUserListItemDTO.model_validate(item.model_dump())


def _user_detail_dto(detail) -> AdminUserDetailDTO:
    return AdminUserDetailDTO(
        **detail.model_dump(exclude={"discount_rules"}),
        discount_rules=[CollaboratorDiscountRuleDTO.model_validate(rule) for rule in detail.discount_rules],
    )


def _config_item_dto(item) -> AdminUserConfigItemDTO:
    return AdminUserConfigItemDTO.model_validate(item.model_dump())


@router.get("", response_model=PaginatedUsersResponseDTO)
async def list_users(
    service: UserAdminServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = USER_PAGE_SIZE_DEFAULT,
    q: Annotated[str | None, Query()] = None,
) -> PaginatedUsersResponseDTO:
    result = await service.list_users(page=page, page_size=page_size, query=q)
    return PaginatedUsersResponseDTO(
        users=[_user_list_item_dto(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total_items=result.total_items,
        total_pages=result.total_pages,
    )


@router.get("/{user_id}", response_model=AdminUserDetailDTO)
async def get_user_detail(
    user_id: Annotated[int, Path()],
    service: UserAdminServiceDep,
) -> AdminUserDetailDTO:
    return _user_detail_dto(await service.get_user_detail(user_id))


@router.get("/{user_id}/configs", response_model=AdminUserConfigListResponseDTO)
async def list_user_configs(
    user_id: Annotated[int, Path()],
    service: UserAdminServiceDep,
) -> AdminUserConfigListResponseDTO:
    configs = await service.list_user_configs(user_id)
    return AdminUserConfigListResponseDTO(configs=[_config_item_dto(item) for item in configs])


@router.get("/{user_id}/configs/{config_id}", response_model=AdminUserConfigDetailDTO)
async def get_user_config_detail(
    user_id: Annotated[int, Path()],
    config_id: Annotated[str, Path()],
    service: UserAdminServiceDep,
) -> AdminUserConfigDetailDTO:
    detail = await service.get_user_config_detail(user_id, config_id)
    return AdminUserConfigDetailDTO.model_validate(detail.model_dump())


@router.post("/{user_id}/block", response_model=AdminUserDetailDTO)
async def block_user(
    user_id: Annotated[int, Path()],
    body: BlockUserDTO,
    service: UserAdminServiceDep,
    admin_telegram_id: Annotated[str, Depends(verify_admin_telegram_id)],
) -> AdminUserDetailDTO:
    detail = await service.block_user(
        user_id,
        admin_telegram_id=admin_telegram_id,
        reason=body.reason,
    )
    return _user_detail_dto(detail)


@router.post("/{user_id}/unblock", response_model=AdminUserDetailDTO)
async def unblock_user(
    user_id: Annotated[int, Path()],
    service: UserAdminServiceDep,
    admin_telegram_id: Annotated[str, Depends(verify_admin_telegram_id)],
) -> AdminUserDetailDTO:
    detail = await service.unblock_user(user_id, admin_telegram_id=admin_telegram_id)
    return _user_detail_dto(detail)


@router.post("/{user_id}/configs/{config_id}/enable", response_model=AdminUserConfigDetailDTO)
async def enable_config(
    user_id: Annotated[int, Path()],
    config_id: Annotated[str, Path()],
    service: UserAdminServiceDep,
    admin_telegram_id: Annotated[str, Depends(verify_admin_telegram_id)],
) -> AdminUserConfigDetailDTO:
    detail = await service.enable_config(
        user_id,
        config_id,
        admin_telegram_id=admin_telegram_id,
    )
    return AdminUserConfigDetailDTO.model_validate(detail.model_dump())


@router.post("/{user_id}/configs/{config_id}/disable", response_model=AdminUserConfigDetailDTO)
async def disable_config(
    user_id: Annotated[int, Path()],
    config_id: Annotated[str, Path()],
    service: UserAdminServiceDep,
    admin_telegram_id: Annotated[str, Depends(verify_admin_telegram_id)],
) -> AdminUserConfigDetailDTO:
    detail = await service.disable_config(
        user_id,
        config_id,
        admin_telegram_id=admin_telegram_id,
    )
    return AdminUserConfigDetailDTO.model_validate(detail.model_dump())


@router.post("/{user_id}/configs/{config_id}/regenerate", response_model=AdminUserConfigDetailDTO)
async def regenerate_config(
    user_id: Annotated[int, Path()],
    config_id: Annotated[str, Path()],
    service: UserAdminServiceDep,
    admin_telegram_id: Annotated[str, Depends(verify_admin_telegram_id)],
) -> AdminUserConfigDetailDTO:
    detail = await service.regenerate_config(
        user_id,
        config_id,
        admin_telegram_id=admin_telegram_id,
    )
    return AdminUserConfigDetailDTO.model_validate(detail.model_dump())


@router.post("/{user_id}/collaborator", response_model=AdminUserDetailDTO)
async def add_collaborator_discount(
    user_id: Annotated[int, Path()],
    body: AddCollaboratorDiscountDTO,
    service: UserAdminServiceDep,
    admin_telegram_id: Annotated[str, Depends(verify_admin_telegram_id)],
) -> AdminUserDetailDTO:
    detail = await service.add_collaborator_discount(
        user_id,
        admin_telegram_id=admin_telegram_id,
        discount_percent=body.discount_percent,
        service_type=body.service_type,
    )
    return _user_detail_dto(detail)


@router.delete("/{user_id}/collaborator", response_model=AdminUserDetailDTO)
async def remove_collaborator(
    user_id: Annotated[int, Path()],
    service: UserAdminServiceDep,
    admin_telegram_id: Annotated[str, Depends(verify_admin_telegram_id)],
) -> AdminUserDetailDTO:
    detail = await service.remove_collaborator(user_id, admin_telegram_id=admin_telegram_id)
    return _user_detail_dto(detail)
