from ubinascii import hexlify

from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    CardanoAddressType,
    CardanoCertificateType,
)
from trezor.strings import format_amount
from trezor.ui.button import ButtonDefault
from trezor.ui.scroll import Paginated
from trezor.ui.text import BR, Text
from trezor.utils import chunks

from apps.common.confirm import confirm, require_confirm, require_hold_to_confirm
from apps.common.layout import address_n_to_str, paginate_lines, show_warning
from apps.common.paths import break_address_n_to_lines

from .helpers import protocol_magics
from .helpers.utils import to_account_path

if False:
    from typing import List
    from trezor import wire
    from trezor.messages import (
        CardanoBlockchainPointerType,
        CardanoTxCertificateType,
        CardanoTxWithdrawalType,
    )
    from trezor.messages.CardanoAddressParametersType import EnumTypeCardanoAddressType


ADDRESS_TYPE_NAMES = {
    CardanoAddressType.BYRON: "Legacy",
    CardanoAddressType.BASE: "Base",
    CardanoAddressType.POINTER: "Pointer",
    CardanoAddressType.ENTERPRISE: "Enterprise",
    CardanoAddressType.REWARD: "Reward",
}

CERTIFICATE_TYPE_NAMES = {
    CardanoCertificateType.STAKE_REGISTRATION: "Stake key registration",
    CardanoCertificateType.STAKE_DEREGISTRATION: "Stake key deregistration",
    CardanoCertificateType.STAKE_DELEGATION: "Stake delegation",
}


def format_coin_amount(amount: int) -> str:
    return "%s %s" % (format_amount(amount, 6), "ADA")


async def confirm_sending(ctx: wire.Context, amount: int, to: str):
    # fmt: off
    lines = [
        "Confirm sending:", BR,
        ui.BOLD, format_coin_amount(amount), BR,
        ui.NORMAL, "to", BR,
    ]
    # fmt: on
    for to_line in chunks(to, 17):
        lines.extend([ui.BOLD, to_line, BR])

    paginated = paginate_lines(lines, "Confirm transaction", ui.ICON_SEND, ui.GREEN)
    await require_confirm(ctx, paginated)


async def show_warning_tx_no_staking_info(
    ctx: wire.Context, address_type: EnumTypeCardanoAddressType, amount: int
):
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Change " + ADDRESS_TYPE_NAMES[address_type].lower())
    page1.normal("address has no stake")
    page1.normal("rights.")
    page1.normal("Change amount:")
    page1.bold(format_coin_amount(amount))

    await require_confirm(ctx, page1)


async def show_warning_tx_pointer_address(
    ctx: wire.Context,
    pointer: CardanoBlockchainPointerType,
    amount: int,
):
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Change address has a")
    page1.normal("pointer with staking")
    page1.normal("rights.")

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Pointer:")
    page2.bold(
        "%s, %s, %s"
        % (pointer.block_index, pointer.tx_index, pointer.certificate_index)
    )
    page2.normal("Change amount:")
    page2.bold(format_coin_amount(amount))

    await require_confirm(ctx, Paginated([page1, page2]))


async def show_warning_tx_different_staking_account(
    ctx: wire.Context,
    staking_account_path: List[int],
    amount: int,
):
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Change address staking")
    page1.normal("rights do not match")
    page1.normal("the current account.")

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Staking account:")
    page2.bold(address_n_to_str(staking_account_path))
    page2.normal("Change amount:")
    page2.bold(format_coin_amount(amount))

    await require_confirm(ctx, Paginated([page1, page2]))


async def show_warning_tx_staking_key_hash(
    ctx: wire.Context,
    staking_key_hash: bytes,
    amount: int,
):
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Change address staking")
    page1.normal("rights do not match")
    page1.normal("the current account.")

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Staking key hash:")
    page2.mono(*chunks(hexlify(staking_key_hash), 17))

    page3 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page3.normal("Change amount:")
    page3.bold(format_coin_amount(amount))

    await require_confirm(ctx, Paginated([page1, page2, page3]))


async def confirm_transaction(
    ctx, amount: int, fee: int, protocol_magic: int, has_metadata: bool
) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Transaction amount:")
    page1.bold(format_coin_amount(amount))
    page1.normal("Transaction fee:")
    page1.bold(format_coin_amount(fee))

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Network:")
    page2.bold(protocol_magics.to_ui_string(protocol_magic))
    if has_metadata:
        page2.normal("Transaction contains")
        page2.normal("metadata")

    await require_hold_to_confirm(ctx, Paginated([page1, page2]))


async def confirm_certificate(
    ctx: wire.Context, certificate: CardanoTxCertificateType
) -> bool:
    pages = []

    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Confirm:")
    page1.bold(CERTIFICATE_TYPE_NAMES[certificate.type])
    page1.normal("for account:")
    page1.bold(address_n_to_str(to_account_path(certificate.path)))
    pages.append(page1)

    if certificate.type == CardanoCertificateType.STAKE_DELEGATION:
        page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
        page2.normal("to pool:")
        page2.bold(hexlify(certificate.pool).decode())
        pages.append(page2)

    await require_confirm(ctx, Paginated(pages))


async def confirm_withdrawal(
    ctx: wire.Context, withdrawal: CardanoTxWithdrawalType
) -> bool:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Confirm withdrawal")
    page1.normal("for account:")
    page1.bold(address_n_to_str(to_account_path(withdrawal.path)))
    page1.normal("Amount:")
    page1.bold(format_coin_amount(withdrawal.amount))

    await require_confirm(ctx, page1)


async def show_address(
    ctx: wire.Context,
    address: str,
    address_type: EnumTypeCardanoAddressType,
    path: List[int],
    network: str = None,
) -> bool:
    """
    Custom show_address function is needed because cardano addresses don't
    fit on a single screen.
    """

    address_type_label = "%s address" % ADDRESS_TYPE_NAMES[address_type]
    lines = []

    if network is not None:
        lines.extend(["%s network" % network, BR])

    for path_line in break_address_n_to_lines(path):
        lines.extend([ui.MONO, path_line, BR])

    for address_line in chunks(address, 17):
        lines.extend([ui.BOLD, address_line, BR])

    paginated = paginate_lines(lines, address_type_label, ui.ICON_RECEIVE, ui.GREEN)

    return await confirm(
        ctx,
        paginated,
        code=ButtonRequestType.Address,
        cancel="QR",
        cancel_style=ButtonDefault,
    )


async def show_warning_address_foreign_staking_key(
    ctx: wire.Context,
    account_path: List[int],
    staking_account_path: List[int],
    staking_key_hash: bytes,
) -> None:
    await show_warning(
        ctx,
        (
            "Stake rights associated",
            "with this address do",
            "not match your",
            "account",
            address_n_to_str(account_path),
        ),
        button="Ok",
    )

    if staking_account_path:
        staking_key_message = (
            "Stake account path:",
            address_n_to_str(staking_account_path),
        )
    else:
        staking_key_message = ("Staking key:", hexlify(staking_key_hash).decode())

    await show_warning(
        ctx,
        staking_key_message,
        button="Ok",
    )


async def show_warning_address_pointer(
    ctx: wire.Context, pointer: CardanoBlockchainPointerType
) -> None:
    await show_warning(
        ctx,
        (
            "Pointer address:",
            "Block: %s" % pointer.block_index,
            "Transaction: %s" % pointer.tx_index,
            "Certificate: %s" % pointer.certificate_index,
        ),
        button="Ok",
    )
