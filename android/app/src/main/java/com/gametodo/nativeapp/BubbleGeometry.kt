package com.gametodo.nativeapp

/** 원형 아이콘 드래그/패널 배치의 수학적 부분. Android UI 없이 단위 테스트 가능. */
object BubbleGeometry {
    data class Point(val x: Int, val y: Int)
    fun clampBubble(x: Int, y: Int, screenWidth: Int, screenHeight: Int,
                    size: Int, topInset: Int, bottomInset: Int,
                    leftInset: Int=0, rightInset: Int=0): Point {
        val maxX=(screenWidth-size-rightInset).coerceAtLeast(0)
        val maxY=(screenHeight-size-bottomInset).coerceAtLeast(0)
        return Point(x.coerceIn(leftInset.coerceIn(0,maxX),maxX),
            y.coerceIn(topInset.coerceIn(0,maxY),maxY))
    }

    fun panelPoint(bubbleX: Int, bubbleY: Int, bubbleSize: Int,
                   panelWidth: Int, panelHeight: Int,
                   screenWidth: Int, screenHeight: Int, gap: Int, topInset: Int,
                   bottomInset: Int, leftInset:Int=0, rightInset:Int=0): Point {
        val maxX=(screenWidth-panelWidth-rightInset).coerceAtLeast(0)
        val x=bubbleX.coerceIn(leftInset.coerceIn(0,maxX),maxX)
        val below = bubbleY + bubbleSize + gap
        val above = bubbleY - panelHeight - gap
        val y = if (below + panelHeight <= screenHeight - bottomInset) below else
            above.coerceAtLeast(topInset)
        return Point(x, y.coerceIn(topInset,
            (screenHeight - panelHeight - bottomInset).coerceAtLeast(topInset)))
    }
}
