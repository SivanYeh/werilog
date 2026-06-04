let app;
let diagram_layer;
let drag_state = {
    is_wiring: false,
    start_port: null,
    temp_graphics: null,
    hovered_port: null,
    
    is_dragging_module: false,
    drag_mod: null,
    drag_offset: {x: 0, y: 0},
    
    is_resizing_module: false,
    resize_mod: null,
    resize_bg: null,
    resize_handle: null,
    resize_start: {x: 0, y: 0},
    resize_start_w: 0,
    resize_start_h: 0
};

let editor;
let timeout_id = null;
let shiftPressed = false;

window.addEventListener('keydown', (e) => { if (e.key === 'Shift') shiftPressed = true; });
window.addEventListener('keyup', (e) => { if (e.key === 'Shift') shiftPressed = false; });

function logToUI(msg) {
    const log_panel = document.getElementById('log-output');
    if (log_panel) {
        const color = (msg.includes('[ERROR]') || msg.includes('[Error]')) ? '#f44336' : '#4caf50';
        log_panel.innerHTML += `<span style="color: ${color}">${msg}</span>\n`;
        log_panel.scrollTop = log_panel.scrollHeight;
    }
    console.log(msg);
}

function clearLogs() {
    const log_panel = document.getElementById('log-output');
    if (log_panel) {
        log_panel.innerHTML = "";
    }
}

function initPixi() {
    app = new PIXI.Application({
        backgroundColor: 0x1e1e24,
        resizeTo: document.getElementById('diagram-container'),
        antialias: true,
        resolution: window.devicePixelRatio || 1,
        autoDensity: true
    });
    document.getElementById('diagram-container').appendChild(app.view);
    
    const resizeObserver = new ResizeObserver(() => {
        if (app) app.resize();
    });
    resizeObserver.observe(document.getElementById('diagram-container'));
    
    diagram_layer = new PIXI.Container();
    app.stage.addChild(diagram_layer);
    
    let currentZoom = 1.0;
    
    document.getElementById('btn-zoom-in').addEventListener('click', () => {
        currentZoom = Math.min(3.0, currentZoom + 0.1);
        diagram_layer.scale.set(currentZoom);
    });
    
    document.getElementById('btn-zoom-out').addEventListener('click', () => {
        currentZoom = Math.max(0.2, currentZoom - 0.1);
        diagram_layer.scale.set(currentZoom);
    });
    
    document.getElementById('btn-zoom-reset').addEventListener('click', () => {
        currentZoom = 1.0;
        diagram_layer.scale.set(currentZoom);
        diagram_layer.position.set(0, 0);
    });
    
    // Background for panning
    const bgInteractive = new PIXI.Graphics();
    bgInteractive.beginFill(0x1e1e24);
    bgInteractive.drawRect(-100000, -100000, 200000, 200000);
    bgInteractive.endFill();
    bgInteractive.eventMode = 'static';
    diagram_layer.addChildAt(bgInteractive, 0);
    
    let isPanning = false;
    let panStart = {x: 0, y: 0};
    
    bgInteractive.on('pointerdown', (e) => {
        isPanning = true;
        panStart = { x: e.global.x - diagram_layer.x, y: e.global.y - diagram_layer.y };
    });
    
    // Minimap implementation
    const minimapW = 200;
    const minimapH = 150;
    const minimapScale = minimapW / 4000;
    
    const minimapContainer = new PIXI.Container();
    app.stage.addChild(minimapContainer);
    
    const updateMinimapPos = () => {
        minimapContainer.x = 20;
        minimapContainer.y = app.renderer.screen.height - minimapH - 20;
    };
    app.renderer.on('resize', updateMinimapPos);
    updateMinimapPos();
    
    const minimapBg = new PIXI.Graphics();
    minimapBg.beginFill(0x000000, 0.7);
    minimapBg.lineStyle(2, 0x555555, 1);
    minimapBg.drawRect(0, 0, minimapW, minimapH);
    minimapBg.endFill();
    minimapContainer.addChild(minimapBg);
    
    const minimapTexture = PIXI.RenderTexture.create({ width: minimapW, height: minimapH });
    const minimapSprite = new PIXI.Sprite(minimapTexture);
    minimapContainer.addChild(minimapSprite);
    
    const viewportBox = new PIXI.Graphics();
    viewportBox.eventMode = 'static';
    viewportBox.cursor = 'move';
    minimapContainer.addChild(viewportBox);
    
    const minimapHandle = new PIXI.Graphics();
    minimapHandle.beginFill(0xffffff);
    minimapHandle.drawRect(0, 0, 8, 8);
    minimapHandle.endFill();
    minimapHandle.eventMode = 'static';
    minimapHandle.cursor = 'nwse-resize';
    minimapContainer.addChild(minimapHandle);
    
    minimapBg.eventMode = 'static';
    minimapBg.cursor = 'pointer';
    
    let isMinimapDragging = false;
    let isMinimapResizing = false;
    let isViewportDragging = false;
    let viewportDragOffset = {x: 0, y: 0};
    let minimapResizeStart = null;
    
    const updateCameraFromMinimap = (e) => {
        const localPos = minimapContainer.toLocal(e.global);
        const scaleX = diagram_layer.scale.x;
        const vw = app.renderer.screen.width / scaleX * minimapScale;
        const vh = app.renderer.screen.height / scaleX * minimapScale;
        
        const vx = localPos.x - vw / 2;
        const vy = localPos.y - vh / 2;
        
        diagram_layer.x = -(vx - 10) / minimapScale * scaleX;
        diagram_layer.y = -(vy - 10) / minimapScale * scaleX;
    };
    
    minimapBg.on('pointerdown', (e) => {
        isMinimapDragging = true;
        updateCameraFromMinimap(e);
        e.stopPropagation();
    });
    
    viewportBox.on('pointerdown', (e) => {
        isViewportDragging = true;
        const localPos = minimapContainer.toLocal(e.global);
        
        const scaleX = diagram_layer.scale.x;
        const vw = app.renderer.screen.width / scaleX * minimapScale;
        const vh = app.renderer.screen.height / scaleX * minimapScale;
        const vx = (-diagram_layer.x / scaleX) * minimapScale + 10;
        const vy = (-diagram_layer.y / scaleX) * minimapScale + 10;
        
        const centerX = vx + vw / 2;
        const centerY = vy + vh / 2;
        
        viewportDragOffset = {
            x: localPos.x - centerX,
            y: localPos.y - centerY
        };
        e.stopPropagation();
    });
    
    minimapHandle.on('pointerdown', (e) => {
        isMinimapResizing = true;
        minimapResizeStart = {
            x: e.global.x,
            y: e.global.y,
            startScale: diagram_layer.scale.x
        };
        e.stopPropagation();
    });
    
    app.stage.eventMode = 'static';
    app.stage.hitArea = new PIXI.Rectangle(-100000, -100000, 200000, 200000);
    
    app.stage.on('pointermove', (e) => {
        if (drag_state.is_wiring && drag_state.temp_graphics) {
            const g = drag_state.temp_graphics;
            g.clear();
            const start = drag_state.start_port;
            const mouse_pos = diagram_layer.toLocal(e.global);
            
            g.lineStyle(2, 0xc586c0, 1);
            g.moveTo(start.x, start.y);
            g.lineTo(mouse_pos.x, mouse_pos.y);
        }
        if (isPanning) {
            diagram_layer.x = e.global.x - panStart.x;
            diagram_layer.y = e.global.y - panStart.y;
        }
        if (isMinimapDragging) {
            updateCameraFromMinimap(e);
        }
        if (isViewportDragging) {
            const localPos = minimapContainer.toLocal(e.global);
            const targetCenterX = localPos.x - viewportDragOffset.x;
            const targetCenterY = localPos.y - viewportDragOffset.y;
            
            const scaleX = diagram_layer.scale.x;
            const vw = app.renderer.screen.width / scaleX * minimapScale;
            const vh = app.renderer.screen.height / scaleX * minimapScale;
            
            const vx = targetCenterX - vw / 2;
            const vy = targetCenterY - vh / 2;
            
            diagram_layer.x = -(vx - 10) / minimapScale * scaleX;
            diagram_layer.y = -(vy - 10) / minimapScale * scaleX;
        }
        if (isMinimapResizing) {
            const startW = app.renderer.screen.width / minimapResizeStart.startScale * minimapScale;
            const newW = startW + (e.global.x - minimapResizeStart.x);
            
            if (newW > 5) {
                let newScale = app.renderer.screen.width / newW * minimapScale;
                newScale = Math.max(0.1, Math.min(newScale, 5.0));
                
                const ratio = newScale / diagram_layer.scale.x;
                diagram_layer.scale.set(newScale);
                diagram_layer.x *= ratio;
                diagram_layer.y *= ratio;
            }
        }
        if (drag_state.is_dragging_module && drag_state.drag_mod) {
            const dx = (e.global.x - drag_state.drag_start_mouse.x) / diagram_layer.scale.x;
            const dy = (e.global.y - drag_state.drag_start_mouse.y) / diagram_layer.scale.y;
            drag_state.drag_mod.container.x = drag_state.drag_start_pos.x + dx;
            drag_state.drag_mod.container.y = drag_state.drag_start_pos.y + dy;
            
            // Stretch wires visually to prevent detachment while dragging
            if (drag_state.drag_mod.is_instance && drag_state.drag_mod.parentData && drag_state.drag_mod.parentData.routed_wires) {
                const modData = drag_state.drag_mod.parentData;
                const modX = modData.box.x;
                const modY = modData.box.y;
                
                const oldInstX = drag_state.drag_start_pos.x + modX;
                const oldInstY = drag_state.drag_start_pos.y + modY;
                const oldInstW = drag_state.drag_mod.box.w;
                const oldInstH = drag_state.drag_mod.box.h;
                
                drag_state.drag_mod.localWires.clear();
                
                modData.routed_wires.forEach(res => {
                    // Copy path so we don't mutate the original while dragging
                    const stretchedPath = res.path.map(pt => [...pt]);
                    
                    const p0 = stretchedPath[0];
                    if (Math.abs(p0[0] - (oldInstX + oldInstW)) < 5 && p0[1] >= oldInstY - 5 && p0[1] <= oldInstY + oldInstH + 5) {
                        p0[0] += dx;
                        p0[1] += dy;
                        // Keep the first segment horizontal if it was horizontal
                        if (stretchedPath.length > 1 && Math.abs(res.path[0][1] - res.path[1][1]) < 0.1) {
                            stretchedPath[1][1] = p0[1];
                        }
                    }
                    
                    const pEnd = stretchedPath[stretchedPath.length - 1];
                    if (Math.abs(pEnd[0] - oldInstX) < 5 && pEnd[1] >= oldInstY - 5 && pEnd[1] <= oldInstY + oldInstH + 5) {
                        pEnd[0] += dx;
                        pEnd[1] += dy;
                        // Keep the last segment horizontal if it was horizontal
                        if (stretchedPath.length > 1 && Math.abs(res.path[res.path.length-1][1] - res.path[res.path.length-2][1]) < 0.1) {
                            stretchedPath[stretchedPath.length-2][1] = pEnd[1];
                        }
                    }
                    
                    drawRoutedPath(drag_state.drag_mod.localWires, stretchedPath, res.jumps, modX, modY);
                });
            }
        }
        if (drag_state.is_resizing_module && drag_state.resize_mod) {
            const dw = (e.global.x - drag_state.resize_start.x) / diagram_layer.scale.x;
            const dh = (e.global.y - drag_state.resize_start.y) / diagram_layer.scale.y;
            
            drag_state.resize_mod.box.w = Math.max(50, drag_state.resize_start_w + dw);
            drag_state.resize_mod.box.h = Math.max(50, drag_state.resize_start_h + dh);
            const new_w = Math.max(50, drag_state.resize_start_w + dw);
            const new_h = Math.max(50, drag_state.resize_start_h + dh);
            
            drag_state.resize_mod.box.w = new_w;
            drag_state.resize_mod.box.h = new_h;
            
            drag_state.resize_bg.clear();
            drawRoundedRect(drag_state.resize_bg, 0, 0, new_w, new_h, 8, 0x1e1e1e, 0x007acc);
            
            drag_state.resize_handle.x = new_w - 15;
            drag_state.resize_handle.y = new_h - 15;
            
            if (drag_state.resize_mod.title) {
                drag_state.resize_mod.title.x = new_w / 2;
                if (!drag_state.resize_mod.is_instance) drag_state.resize_mod.title.y = new_h - 15;
                else drag_state.resize_mod.title.y = new_h / 2;
            }
            
            // we should also move the outPorts to stick to the right edge
            if (drag_state.resize_mod.outPorts) {
                drag_state.resize_mod.outPorts.forEach(p => {
                    p.x = new_w;
                });
            }
            
            // Stretch wires visually to prevent lag feeling
            if (drag_state.resize_mod.localWires) {
                drag_state.resize_mod.localWires.clear();
                
                if (!drag_state.resize_mod.is_instance && drag_state.resize_mod.data.routed_wires) {
                    const modData = drag_state.resize_mod.data;
                    const modX = modData.box.x;
                    const modY = modData.box.y;
                    
                    modData.routed_wires.forEach(res => {
                        const stretchedPath = res.path.map(pt => {
                            const isRightEdge = pt[0] >= drag_state.resize_start_w + modX - 5;
                            const nx = isRightEdge ? pt[0] + dw : pt[0];
                            return [nx, pt[1]];
                        });
                        drawRoutedPath(drag_state.resize_mod.localWires, stretchedPath, res.jumps, modX, modY);
                    });
                } else if (drag_state.resize_mod.is_instance && drag_state.resize_mod.parentData && drag_state.resize_mod.parentData.routed_wires) {
                    const modData = drag_state.resize_mod.parentData;
                    const modX = modData.box.x;
                    const modY = modData.box.y;
                    
                    const oldInstX = drag_state.resize_start.x - drag_state.resize_start_w; // this is not quite right, but we can compute from box
                    
                    // The resize_mod box X/Y are relative.
                    const instRelativeX = drag_state.resize_mod.container.x;
                    const instRelativeY = drag_state.resize_mod.container.y;
                    const oldInstAbsoluteX = instRelativeX + modX;
                    const oldInstAbsoluteY = instRelativeY + modY;
                    const oldInstW = drag_state.resize_start_w;
                    const oldInstH = drag_state.resize_start_h;
                    
                    modData.routed_wires.forEach(res => {
                        const stretchedPath = res.path.map((pt, i) => {
                            let nx = pt[0];
                            let ny = pt[1];
                            
                            // Check if it's the start point (output port of the instance)
                            if (i === 0) {
                                if (Math.abs(pt[0] - (oldInstAbsoluteX + oldInstW)) < 5 && pt[1] >= oldInstAbsoluteY - 5 && pt[1] <= oldInstAbsoluteY + oldInstH + 5) {
                                    nx += dw;
                                }
                            } 
                            
                            return [nx, ny];
                        });
                        drawRoutedPath(drag_state.resize_mod.localWires, stretchedPath, res.jumps, modX, modY);
                    });
                }
            }
        }
    });
    
    const stopGlobalActions = () => {
        isMinimapDragging = false;
        isMinimapResizing = false;
        isViewportDragging = false;
        isPanning = false;
        
        let needsReRender = false;
        
        if (drag_state.is_dragging_module) {
            drag_state.is_dragging_module = false;
            if (drag_state.drag_mod) {
                modulePositions[drag_state.drag_mod.name] = {
                    x: drag_state.drag_mod.container.x,
                    y: drag_state.drag_mod.container.y,
                    w: drag_state.drag_mod.box.w,
                    h: drag_state.drag_mod.box.h
                };
                needsReRender = true;
            }
            drag_state.drag_mod = null;
        }
        
        if (drag_state.is_resizing_module) {
            drag_state.is_resizing_module = false;
            if (drag_state.resize_mod) {
                modulePositions[drag_state.resize_mod.name] = {
                    x: drag_state.resize_mod.container.x,
                    y: drag_state.resize_mod.container.y,
                    w: drag_state.resize_mod.box.w,
                    h: drag_state.resize_mod.box.h
                };
                needsReRender = true;
            }
            drag_state.resize_mod = null;
        }
        
        if (needsReRender && editor) {
            parseAndRender(editor.getValue());
        }
    };
    
    app.stage.on('pointerup', stopGlobalActions);
    app.stage.on('pointerupoutside', stopGlobalActions);
    
    const minimapTransform = new PIXI.Matrix();
    minimapTransform.scale(minimapScale, minimapScale);
    minimapTransform.translate(10, 10);
    
    window.updateMinimapTexture = () => {
        if (!minimapTexture || !diagram_layer) return;
        const oldX = diagram_layer.x;
        const oldY = diagram_layer.y;
        const oldScaleX = diagram_layer.scale.x;
        const oldScaleY = diagram_layer.scale.y;
        
        diagram_layer.position.set(0, 0);
        diagram_layer.scale.set(1, 1);
        bgInteractive.visible = false;
        
        app.renderer.render(diagram_layer, {
            renderTexture: minimapTexture,
            clear: true,
            transform: minimapTransform
        });
        
        bgInteractive.visible = true;
        diagram_layer.position.set(oldX, oldY);
        diagram_layer.scale.set(oldScaleX, oldScaleY);
    };
    
    app.ticker.add(() => {
        const oldX = diagram_layer.x;
        const oldY = diagram_layer.y;
        const oldScaleX = diagram_layer.scale.x;
        
        viewportBox.clear();
        viewportBox.beginFill(0xffffff, 0.001); // nearly invisible but clickable
        viewportBox.lineStyle(1.5, 0x00ff00, 0.8);
        const invScale = 1 / oldScaleX;
        const vw = app.renderer.screen.width * invScale * minimapScale;
        const vh = app.renderer.screen.height * invScale * minimapScale;
        const vx = (-oldX * invScale) * minimapScale + 10;
        const vy = (-oldY * invScale) * minimapScale + 10;
        viewportBox.drawRect(vx, vy, vw, vh);
        viewportBox.endFill();
        
        minimapHandle.x = vx + vw - 4;
        minimapHandle.y = vy + vh - 4;
    });
}

function drawRoundedRect(graphics, x, y, width, height, radius, fillColor, strokeColor) {
    graphics.lineStyle(2, strokeColor, 1);
    graphics.beginFill(fillColor);
    graphics.drawRoundedRect(x, y, width, height, radius);
    graphics.endFill();
}

function drawRoutedPath(graphics, path, jumps, offsetX = 0, offsetY = 0) {
    if (!path || path.length === 0) return;
    
    graphics.lineStyle(2.5, 0xc586c0, 1, 0.5, true);
    graphics.moveTo(path[0][0] - offsetX, path[0][1] - offsetY);
    
    for (let i = 0; i < path.length - 1; i++) {
        const p1 = path[i];
        const p2 = path[i+1];
        
        let segment_jumps = [];
        for (const jump of (jumps || [])) {
            const jx = jump[0], jy = jump[1];
            if (Math.abs(p1[0] - p2[0]) < 1) {
                const min_y = Math.min(p1[1], p2[1]);
                const max_y = Math.max(p1[1], p2[1]);
                if (min_y < jy && jy < max_y && Math.abs(p1[0] - jx) < 1) {
                    segment_jumps.push({jx, jy, orient: "vertical"});
                }
            } else if (Math.abs(p1[1] - p2[1]) < 1) {
                const min_x = Math.min(p1[0], p2[0]);
                const max_x = Math.max(p1[0], p2[0]);
                if (min_x < jx && jx < max_x && Math.abs(p1[1] - jy) < 1) {
                    segment_jumps.push({jx, jy, orient: "horizontal"});
                }
            }
        }
        
        if (segment_jumps.length > 0) {
            if (Math.abs(p1[0] - p2[0]) < 1) {
                const reverse = p1[1] > p2[1];
                segment_jumps.sort((a, b) => reverse ? b.jy - a.jy : a.jy - b.jy);
            } else {
                const reverse = p1[0] > p2[0];
                segment_jumps.sort((a, b) => reverse ? b.jx - a.jx : a.jx - b.jx);
            }
            
            for (const jump of segment_jumps) {
                if (jump.orient === "vertical") {
                    const offset = p1[1] > p2[1] ? -6 : 6;
                    graphics.lineTo(jump.jx - offsetX, jump.jy - offset - offsetY);
                    graphics.arc(jump.jx - offsetX, jump.jy - offsetY, 6, p1[1] < p2[1] ? -Math.PI/2 : Math.PI/2, p1[1] < p2[1] ? Math.PI/2 : -Math.PI/2, false);
                } else {
                    const offset = p1[0] > p2[0] ? -6 : 6;
                    graphics.lineTo(jump.jx - offset - offsetX, jump.jy - offsetY);
                    graphics.arc(jump.jx - offsetX, jump.jy - offsetY, 6, p1[0] < p2[0] ? Math.PI : 0, p1[0] < p2[0] ? 0 : Math.PI, false);
                }
            }
        }
        graphics.lineTo(p2[0] - offsetX, p2[1] - offsetY);
    }
}

function createInteractivePort(x, y, name, direction, modName) {
    const container = new PIXI.Container();
    container.x = x;
    container.y = y;
    
    const g = new PIXI.Graphics();
    const fillHex = direction === "input" ? 0xffcc00 : 0x4ec9b0;
    g.lineStyle(1.5, 0xffffff, 1);
    g.beginFill(fillHex);
    g.drawCircle(0, 0, 6);
    g.endFill();
    
    const text = new PIXI.Text(name, {fontFamily: "system-ui", fontSize: 12, fill: 0xcccccc});
    text.anchor.set(direction === "input" ? 1 : 0, 0.5);
    text.x = direction === "input" ? -12 : 12;
    text.y = 0;
    
    container.addChild(g);
    container.addChild(text);
    
    container.eventMode = 'static';
    container.cursor = 'pointer';
    
    container.on('pointerenter', () => drag_state.hovered_port = { name, direction, mod: modName });
    container.on('pointerleave', () => drag_state.hovered_port = null);
    
    container.on('pointerdown', (e) => {
        e.stopPropagation();
        drag_state.is_wiring = true;
        const globalPos = container.getGlobalPosition();
        const localPos = diagram_layer.toLocal(globalPos);
        drag_state.start_port = { name, direction, x: localPos.x, y: localPos.y, mod: modName };
        drag_state.temp_graphics = new PIXI.Graphics();
        diagram_layer.addChild(drag_state.temp_graphics);
    });
    
    const onPortPointerUp = (e) => {
        e.stopPropagation();
        if (drag_state.is_wiring) {
            const start = drag_state.start_port;
            const target = drag_state.hovered_port;
            if (start && target && start.name !== target.name && start.direction !== target.direction) {
                const getParent = m => m.split('.')[0];
                if (getParent(start.mod) === getParent(target.mod)) {
                    // For nested wiring, if it's an instance, the code needs the instance name prepended
                    // E.g. "trans.clk" if the port name is just "clk"
                    const getFullSigName = (portName, modName) => {
                        return modName.includes('.') ? `${modName.split('.')[1]}.${portName}` : portName;
                    };
                    
                    const src_name = getFullSigName(start.direction === "input" ? start.name : target.name, start.direction === "input" ? start.mod : target.mod);
                    const dst_name = getFullSigName(start.direction === "output" ? start.name : target.name, start.direction === "output" ? start.mod : target.mod);
                    
                    // Actually, for addWireToCode, if we are wiring to an instance, we should edit the instance instantiation in the code.
                    // Or we just add an assign statement for now, or edit the instance connection.
                    // This might be tricky! We can just use addWireToCode for now and let the parser handle it.
                    addWireToCode(src_name, dst_name, getParent(start.mod));
                } else {
                    logToUI(`[Error] Cross-module wiring not yet supported in this prototype.`);
                }
            }
            
            drag_state.is_wiring = false;
            if (drag_state.temp_graphics) {
                diagram_layer.removeChild(drag_state.temp_graphics);
                drag_state.temp_graphics = null;
            }
        }
    };
    
    container.on('pointerup', onPortPointerUp);
    container.on('pointerupoutside', onPortPointerUp);
    
    return container;
}

function addWireToCode(src, dst, modName) {
    logToUI(`[Wiring] Connected ${src} -> ${dst} in ${modName}`);
    if (editor) {
        const code = editor.getValue();
        const lines = code.split("\n");
        let targetLine = -1;
        let inTargetModule = false;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.match(new RegExp(`\\bmodule\\s+${modName}\\b`))) {
                inTargetModule = true;
            }
            if (inTargetModule && line.includes("endmodule")) {
                targetLine = i;
                break;
            }
        }
        
        if (targetLine !== -1) {
            lines.splice(targetLine, 0, `    assign ${dst} = ${src};`);
            editor.setValue(lines.join("\n"));
        } else {
            logToUI(`[Error] Could not find endmodule for ${modName}`);
        }
    }
}

let modulePositions = {};
let current_syntax_errors = [];

function renderLayout(layoutData) {
    diagram_layer.removeChildren();
    
    if (drag_state.temp_graphics) {
        drag_state.temp_graphics = null;
        drag_state.is_wiring = false;
    }
    
    layoutData.forEach(module => {
        const modContainer = new PIXI.Container();
        modContainer.eventMode = 'static';
        modContainer.cursor = 'move';
        
        modContainer.x = module.box.x;
        modContainer.y = module.box.y;
        diagram_layer.addChild(modContainer);
        
        modContainer.on('pointerdown', (e) => {
            drag_state.is_dragging_module = true;
            drag_state.drag_mod = { name: module.name, container: modContainer, box: module.box };
            drag_state.drag_start_pos = { x: modContainer.x, y: modContainer.y };
            drag_state.drag_start_mouse = { x: e.global.x, y: e.global.y };
            e.stopPropagation();
        });
        
        const bg = new PIXI.Graphics();
        drawRoundedRect(bg, 0, 0, module.box.w, module.box.h, 8, 0x2d2d30, 0x555555);
        modContainer.addChild(bg);
        
        const localWires = new PIXI.Graphics();
        modContainer.addChild(localWires);
        
        const title = new PIXI.Text(module.name, {fontFamily: "system-ui", fontSize: 15, fill: 0xffffff, fontWeight: "bold"});
        title.anchor.set(0.5, 1);
        title.x = module.box.w / 2;
        title.y = module.box.h - 15;
        modContainer.addChild(title);
        
        const outPorts = [];
        
        // Save position to prevent jumping on next parse if not moved
        modulePositions[module.name] = {
            x: module.box.x,
            y: module.box.y,
            w: module.box.w,
            h: module.box.h
        };
        
        module.ports.forEach(p => {
            const portMc = createInteractivePort(p.x - module.box.x, p.y - module.box.y, p.name, p.direction, module.name);
            if (p.direction === "output") outPorts.push(portMc);
            modContainer.addChild(portMc);
        });
        
        module.elements.forEach(el => {
            const elBg = new PIXI.Graphics();
            drawRoundedRect(elBg, (el.x - module.box.x) - 30, (el.y - module.box.y) - 15, 60, 30, 4, 0x3e3e42, 0x4ec9b0);
            modContainer.addChild(elBg);
            
            const elTxt = new PIXI.Text(el.op, {fontFamily: "system-ui", fontSize: 11, fill: 0x4ec9b0, fontWeight: "bold"});
            elTxt.anchor.set(0.5, 0.5);
            elTxt.x = el.x - module.box.x;
            elTxt.y = el.y - module.box.y;
            modContainer.addChild(elTxt);
        });
        
        if (module.instances) {
            module.instances.forEach(inst => {
                // Save instance position as RELATIVE to parent module
                modulePositions[`${module.name}.${inst.name}`] = {
                    x: inst.box.x - module.box.x,
                    y: inst.box.y - module.box.y,
                    w: inst.box.w,
                    h: inst.box.h
                };
                
                const instContainer = new PIXI.Container();
                instContainer.x = inst.box.x - module.box.x;
                instContainer.y = inst.box.y - module.box.y;
                modContainer.addChild(instContainer);
                
                const instBg = new PIXI.Graphics();
                drawRoundedRect(instBg, 0, 0, inst.box.w, inst.box.h, 6, 0x3a3a3d, 0x666666);
                instContainer.addChild(instBg);
                
                const instTitle = new PIXI.Text(`${inst.type}\n${inst.name}`, {fontFamily: "system-ui", fontSize: 10, fill: 0xcccccc, align: 'center'});
                instTitle.anchor.set(0.5, 0.5);
                instTitle.x = inst.box.w / 2;
                instTitle.y = inst.box.h / 2;
                instContainer.addChild(instTitle);
                
                inst.ports.forEach(p => {
                    const portMc = createInteractivePort(p.x - inst.box.x, p.y - inst.box.y, p.name, p.direction, `${module.name}.${inst.name}`);
                    if (p.direction === "output") {
                        portMc.isOutPort = true;
                    }
                    instContainer.addChild(portMc);
                });
                
                instContainer.eventMode = 'static';
                instContainer.cursor = 'move';
                
                instContainer.on('pointerdown', (e) => {
                    drag_state.is_dragging_module = true;
                    drag_state.drag_mod = { 
                        name: `${module.name}.${inst.name}`, 
                        container: instContainer, 
                        box: inst.box,
                        is_instance: true,
                        parentData: module,
                        localWires: localWires
                    };
                    drag_state.drag_start_pos = { x: instContainer.x, y: instContainer.y };
                    drag_state.drag_start_mouse = { x: e.global.x, y: e.global.y };
                    e.stopPropagation();
                });
                
                const instResize = new PIXI.Graphics();
                instResize.beginFill(0x888888);
                instResize.moveTo(0, 10);
                instResize.lineTo(10, 10);
                instResize.lineTo(10, 0);
                instResize.endFill();
                instResize.x = inst.box.w - 10;
                instResize.y = inst.box.h - 10;
                instResize.eventMode = 'static';
                instResize.cursor = 'nwse-resize';
                instContainer.addChild(instResize);
                
                instResize.on('pointerdown', (e) => {
                    drag_state.is_resizing_module = true;
                    drag_state.resize_mod = { 
                        name: `${module.name}.${inst.name}`, 
                        container: instContainer, 
                        box: inst.box,
                        title: instTitle,
                        outPorts: instContainer.children.filter(c => c.isOutPort),
                        localWires: localWires, // Note: localWires handles all wires in parent module, not instances!
                        data: inst,
                        parentData: module,
                        is_instance: true
                    };
                    drag_state.resize_bg = instBg;
                    drag_state.resize_handle = instResize;
                    drag_state.resize_start = { x: e.global.x, y: e.global.y };
                    drag_state.resize_start_w = inst.box.w;
                    drag_state.resize_start_h = inst.box.h;
                    drag_state.resize_mod_x = inst.box.x;
                    drag_state.resize_mod_y = inst.box.y;
                    e.stopPropagation();
                });
            });
        }
        
        const resizeHandle = new PIXI.Graphics();
        resizeHandle.beginFill(0x888888);
        resizeHandle.moveTo(0, 15);
        resizeHandle.lineTo(15, 15);
        resizeHandle.lineTo(15, 0);
        resizeHandle.endFill();
        resizeHandle.x = module.box.w - 15;
        resizeHandle.y = module.box.h - 15;
        resizeHandle.eventMode = 'static';
        resizeHandle.cursor = 'nwse-resize';
        modContainer.addChild(resizeHandle);
        
        resizeHandle.on('pointerdown', (e) => {
            drag_state.is_resizing_module = true;
            drag_state.resize_mod = { 
                name: module.name, 
                container: modContainer, 
                box: module.box, 
                title: title, 
                outPorts: outPorts,
                localWires: localWires,
                data: module,
                is_instance: false
            };
            drag_state.resize_bg = bg;
            drag_state.resize_handle = resizeHandle;
            drag_state.resize_start = { x: e.global.x, y: e.global.y };
            drag_state.resize_start_w = module.box.w;
            drag_state.resize_start_h = module.box.h;
            drag_state.resize_mod_x = module.box.x;
            drag_state.resize_mod_y = module.box.y;
            e.stopPropagation();
        });
        
        module.routed_wires.forEach(res => {
            drawRoutedPath(localWires, res.path, res.jumps, module.box.x, module.box.y);
        });
    });
    
    if (window.updateMinimapTexture) {
        window.updateMinimapTexture();
    }
}

async function parseAndRender(text) {
    clearLogs();
    
    try {
        const response = await fetch('/api/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: text, positions: modulePositions })
        });
        
        const responseText = await response.text();
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${responseText}`);
        }
        
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            throw new Error(`Invalid JSON: ${responseText}`);
        }

        
        current_syntax_errors = data.errors || [];
        
        if (data.errors && data.errors.length > 0) {
            data.errors.forEach(err => logToUI(`Line ${err.line_number}: [${err.severity.toUpperCase()}] ${err.message}`));
        }
        
        if (data.layout) {
            window.lastLayoutData = data.layout;
            renderLayout(data.layout);
            logToUI("[System] Diagram updated.");
        }
    } catch (e) {
        logToUI(`[Error] Failed to communicate with backend: ${e}`);
    }
}

function handleTextChange() {
    if (timeout_id) clearTimeout(timeout_id);
    timeout_id = setTimeout(() => {
        if (editor) {
            parseAndRender(editor.getValue());
        }
    }, 500);
}

function setupMonaco() {
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' }});
    require(['vs/editor/editor.main'], function() {
        monaco.languages.register({ id: 'verilog' });
        
        monaco.languages.registerInlineCompletionsProvider('verilog', {
            provideInlineCompletions: async function(model, position, context, token) {
                const line = model.getLineContent(position.lineNumber);
                const prefix = line.substring(0, position.column - 1);
                
                try {
                    const response = await fetch('/api/suggest', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prefix: prefix, errors: current_syntax_errors })
                    });
                    
                    const responseText = await response.text();
                    if (!response.ok) {
                        console.error("Agent completion failed", response.status, responseText);
                        return { items: [] };
                    }
                    
                    let data;
                    try {
                        data = JSON.parse(responseText);
                    } catch (e) {
                        console.error("Agent completion JSON error", e, responseText);
                        return { items: [] };
                    }

                    
                    if (data.suggestion) {
                        return {
                            items: [{
                                insertText: data.suggestion
                            }]
                        };
                    }
                } catch (e) {
                    console.error("Agent completion error", e);
                }
                return { items: [] };
            },
            freeInlineCompletions: function(completions) {}
        });
        
        editor = monaco.editor.create(document.getElementById('editor-container'), {
            value: '/* Upload a Verilog file or type here */\n',
            language: 'verilog',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            inlineSuggest: { enabled: true }
        });
        
        logToUI("[System] Monaco Editor connected.");
        editor.onDidChangeModelContent(handleTextChange);
        
        document.getElementById('file-upload').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (ev) => editor.setValue(ev.target.result);
            reader.readAsText(file);
        });
        
        // Load default code
        fetch('verilog/init.v')
            .then(res => res.text())
            .then(text => {
                editor.setValue(text);
            }).catch(e => console.error(e));
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initPixi();
    setupMonaco();

    document.getElementById('btn-export').addEventListener('click', async () => {
        if (!window.lastLayoutData) {
            logToUI("[Error] No diagram available to export.");
            return;
        }

        let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="3000" height="3000" style="background-color: #1e1e24">`;
        svg += `<style>
            .mod-box { fill: #2d2d30; stroke: #555; stroke-width: 2px; }
            .mod-text { fill: white; font-family: sans-serif; font-size: 14px; }
            .port-in { fill: #ffcc00; stroke: white; stroke-width: 1px; }
            .port-out { fill: #4ec9b0; stroke: white; stroke-width: 1px; }
            .port-text { fill: #cccccc; font-family: sans-serif; font-size: 12px; }
            .el-box { fill: #3e3e42; stroke: #4ec9b0; stroke-width: 2px; }
            .wire { fill: none; stroke: #c586c0; stroke-width: 2.5px; stroke-linejoin: round; }
        </style>`;

        const escapeXml = (unsafe) => {
            if (!unsafe) return "";
            return String(unsafe).replace(/[<>&'"]/g, function (c) {
                switch (c) {
                    case '<': return '&lt;';
                    case '>': return '&gt;';
                    case '&': return '&amp;';
                    case "'": return '&apos;';
                    case '"': return '&quot;';
                }
            });
        };

        window.lastLayoutData.forEach(mod => {
            svg += `<rect x="${mod.box.x}" y="${mod.box.y}" width="${mod.box.w}" height="${mod.box.h}" rx="8" ry="8" class="mod-box" />`;
            svg += `<text x="${mod.box.x + mod.box.w/2}" y="${mod.box.y + mod.box.h - 15}" class="mod-text" text-anchor="middle">${escapeXml(mod.name)}</text>`;

            mod.ports.forEach(p => {
                svg += `<circle cx="${p.x}" cy="${p.y}" r="6" class="${p.direction === 'input' ? 'port-in' : 'port-out'}" />`;
                const textX = p.direction === 'input' ? p.x - 12 : p.x + 12;
                const textAnchor = p.direction === 'input' ? 'end' : 'start';
                svg += `<text x="${textX}" y="${p.y + 4}" class="port-text" text-anchor="${textAnchor}">${escapeXml(p.name)}</text>`;
            });

            mod.elements.forEach(el => {
                if (el.op === "~" || el.op === "not") {
                    svg += `<polygon points="${el.x-12},${el.y-12} ${el.x-12},${el.y+12} ${el.x+8},${el.y}" class="el-box" />`;
                    svg += `<circle cx="${el.x+12}" cy="${el.y}" r="4" class="el-box" />`;
                } else {
                    svg += `<rect x="${el.x-30}" y="${el.y-15}" width="60" height="30" rx="4" ry="4" class="el-box" />`;
                    svg += `<text x="${el.x}" y="${el.y+4}" class="port-text" style="fill:#4ec9b0" text-anchor="middle">${escapeXml(el.op)}</text>`;
                }
            });

            mod.instances.forEach(inst => {
                svg += `<rect x="${inst.box.x}" y="${inst.box.y}" width="${inst.box.w}" height="${inst.box.h}" rx="6" ry="6" class="mod-box" style="fill:#3a3a3d;stroke:#666" />`;
                svg += `<text x="${inst.box.x + inst.box.w/2}" y="${inst.box.y + inst.box.h/2 - 6}" class="mod-text" style="font-size: 10px; fill: #cccccc;" text-anchor="middle">${escapeXml(inst.type)}</text>`;
                svg += `<text x="${inst.box.x + inst.box.w/2}" y="${inst.box.y + inst.box.h/2 + 6}" class="mod-text" style="font-size: 10px; fill: #cccccc;" text-anchor="middle">${escapeXml(inst.name)}</text>`;
                inst.ports.forEach(p => {
                    svg += `<circle cx="${p.x}" cy="${p.y}" r="6" class="${p.direction === 'input' ? 'port-in' : 'port-out'}" />`;
                    const textX = p.direction === 'input' ? p.x - 12 : p.x + 12;
                    const textAnchor = p.direction === 'input' ? 'end' : 'start';
                    svg += `<text x="${textX}" y="${p.y + 4}" class="port-text" text-anchor="${textAnchor}">${escapeXml(p.name)}</text>`;
                });
            });

            mod.routed_wires.forEach(w => {
                if (!w.path || w.path.length < 2) return;
                let d = `M ${w.path[0][0]} ${w.path[0][1]}`;
                for (let i = 1; i < w.path.length; i++) {
                    d += ` L ${w.path[i][0]} ${w.path[i][1]}`;
                }
                svg += `<path d="${d}" class="wire" />`;
            });
        });

        svg += `</svg>`;

        try {
            if (window.showSaveFilePicker) {
                const handle = await window.showSaveFilePicker({
                    suggestedName: 'diagram_export.svg',
                    types: [{
                        description: 'SVG Vector Graphic',
                        accept: {'image/svg+xml': ['.svg']}
                    }]
                });
                const writable = await handle.createWritable();
                await writable.write(svg);
                await writable.close();
                logToUI("[System] SVG exported successfully.");
            } else {
                const blob = new Blob([svg], { type: 'image/svg+xml' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'diagram_export.svg';
                a.click();
                URL.revokeObjectURL(url);
                logToUI("[System] SVG downloaded.");
            }
        } catch (e) {
            if (e.name !== 'AbortError') {
                logToUI(`[Error] SVG Export failed: ${e.message}`);
            }
        }
    });
});
