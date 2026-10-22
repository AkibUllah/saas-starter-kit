from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    OrgContext,
    client_ip,
    current_user,
    get_ctx,
    get_db,
    get_org_context,
    require_role,
)
from app.core.context import AppContext
from app.models import Role, User
from app.schemas.common import Message
from app.schemas.org import (
    AcceptInviteRequest,
    InviteCreate,
    InviteOut,
    InvitePreview,
    MemberOut,
    MemberUpdate,
    OrgCreate,
    OrgOut,
    OrgUpdate,
)
from app.services.invite_service import InviteService
from app.services.org_service import OrgService

router = APIRouter(tags=["organizations"])


def _org_out(org, role: Role) -> OrgOut:  # type: ignore[no-untyped-def]
    return OrgOut(
        id=org.id, name=org.name, slug=org.slug, plan=org.plan, role=role, created_at=org.created_at
    )


@router.get("/orgs", response_model=list[OrgOut])
async def list_orgs(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> list[OrgOut]:
    return [_org_out(org, role) for org, role in await OrgService(db, ctx).list_for_user(user)]


@router.post("/orgs", response_model=OrgOut, status_code=201)
async def create_org(
    body: OrgCreate,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> OrgOut:
    org = await OrgService(db, ctx).create(user, body.name, body.slug, ip=client_ip(request))
    return _org_out(org, Role.OWNER)


@router.get("/orgs/{org_id}", response_model=OrgOut)
async def get_org(octx: OrgContext = Depends(get_org_context)) -> OrgOut:
    return _org_out(octx.org, octx.role or Role.MEMBER)


@router.patch("/orgs/{org_id}", response_model=OrgOut)
async def update_org(
    body: OrgUpdate,
    request: Request,
    octx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> OrgOut:
    assert octx.user is not None
    org = await OrgService(db, ctx).update(
        octx.org, octx.user, name=body.name, ip=client_ip(request)
    )
    return _org_out(org, octx.role or Role.MEMBER)


@router.delete("/orgs/{org_id}", response_model=Message)
async def delete_org(
    request: Request,
    octx: OrgContext = Depends(require_role(Role.OWNER)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Message:
    assert octx.user is not None
    await OrgService(db, ctx).delete(octx.org, octx.user, ip=client_ip(request))
    return Message(detail="organization deleted")


# ---------------------------------------------------------------- members
@router.get("/orgs/{org_id}/members", response_model=list[MemberOut])
async def list_members(
    octx: OrgContext = Depends(require_role(Role.MEMBER)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> list[MemberOut]:
    return [
        MemberOut(
            user_id=u.id, email=u.email, full_name=u.full_name, role=m.role, joined_at=m.created_at
        )
        for m, u in await OrgService(db, ctx).members(octx.org)
    ]


@router.patch("/orgs/{org_id}/members/{user_id}", response_model=MemberOut)
async def change_role(
    user_id: str,
    body: MemberUpdate,
    request: Request,
    octx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> MemberOut:
    assert octx.user is not None and octx.role is not None
    svc = OrgService(db, ctx)
    membership = await svc.change_role(
        octx.org, octx.user, octx.role, user_id, body.role, ip=client_ip(request)
    )
    target = await db.get(User, user_id)
    assert target is not None
    return MemberOut(
        user_id=target.id,
        email=target.email,
        full_name=target.full_name,
        role=membership.role,
        joined_at=membership.created_at,
    )


@router.delete("/orgs/{org_id}/members/{user_id}", response_model=Message)
async def remove_member(
    user_id: str,
    request: Request,
    octx: OrgContext = Depends(require_role(Role.MEMBER)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Message:
    assert octx.user is not None and octx.role is not None
    await OrgService(db, ctx).remove_member(
        octx.org, octx.user, octx.role, user_id, ip=client_ip(request)
    )
    return Message(detail="member removed")


# ---------------------------------------------------------------- invites
@router.get("/orgs/{org_id}/invites", response_model=list[InviteOut])
async def list_invites(
    octx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> list:
    return await InviteService(db, ctx).list(octx.org)


@router.post("/orgs/{org_id}/invites", response_model=InviteOut, status_code=201)
async def create_invite(
    body: InviteCreate,
    request: Request,
    octx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
):  # type: ignore[no-untyped-def]
    assert octx.user is not None and octx.role is not None
    invite, _ = await InviteService(db, ctx).create(
        octx.org, octx.user, octx.role, email=body.email, role=body.role, ip=client_ip(request)
    )
    return invite


@router.delete("/orgs/{org_id}/invites/{invite_id}", response_model=InviteOut)
async def revoke_invite(
    invite_id: str,
    request: Request,
    octx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
):  # type: ignore[no-untyped-def]
    assert octx.user is not None
    return await InviteService(db, ctx).revoke(
        octx.org, octx.user, invite_id, ip=client_ip(request)
    )


@router.get("/invites/preview", response_model=InvitePreview)
async def preview_invite(
    token: str, db: AsyncSession = Depends(get_db), ctx: AppContext = Depends(get_ctx)
) -> InvitePreview:
    invite, org, status = await InviteService(db, ctx).preview(token)
    return InvitePreview(
        org_name=org.name,
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
        status=status,
    )


@router.post("/invites/accept", response_model=OrgOut)
async def accept_invite(
    body: AcceptInviteRequest,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> OrgOut:
    membership, org = await InviteService(db, ctx).accept(body.token, user, ip=client_ip(request))
    return _org_out(org, membership.role)
